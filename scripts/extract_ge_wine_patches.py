#!/usr/bin/env python3
"""Extract GE-only Wine patches from a proton-ge-custom checkout.

This script treats proton-ge-custom as a wrapper repository and emits only the
patch delta carried by its Wine source tree relative to the upstream Wine base.

Typical usage:
    python3 scripts/extract_ge_wine_patches.py \
        --ge-root /path/to/proton-ge-custom \
        --output-dir patches/ge-wine-only
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def run(cmd: List[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def git(cmd: List[str], cwd: Path, check: bool = True) -> str:
    return run(["git"] + cmd, cwd=cwd, check=check)


def detect_wine_dir(ge_root: Path) -> Path:
    candidates = [
        ge_root / "wine",
        ge_root / "proton-wine",
        ge_root,
    ]
    for candidate in candidates:
        if (candidate / "dlls" / "ntdll" / "loader.c").exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate a Wine source tree under {ge_root}. "
        "Expected wine/, proton-wine/, or the repo root to contain dlls/ntdll/loader.c"
    )


def detect_default_upstream_ref(wine_dir: Path) -> str:
    try:
        head = git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=wine_dir)
        return head.replace("refs/remotes/", "")
    except subprocess.CalledProcessError:
        pass
    for candidate in ("origin/master", "origin/main", "origin/staging", "origin/wine-10.0"):
        try:
            git(["rev-parse", "--verify", candidate], cwd=wine_dir)
            return candidate
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError("Could not determine an upstream remote ref for the GE wine tree")


def top_level_counts(wine_dir: Path, base_ref: str) -> Dict[str, int]:
    names = git(["diff", "--name-only", f"{base_ref}..HEAD"], cwd=wine_dir).splitlines()
    counts: Dict[str, int] = {}
    for name in names:
        top = name.split("/", 1)[0] if "/" in name else name
        counts[top] = counts.get(top, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ge-root", required=True, help="Path to a proton-ge-custom checkout")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where extracted patch files and inventory will be written",
    )
    parser.add_argument(
        "--upstream-ref",
        default="",
        help="Optional upstream ref inside the GE wine repo to diff against, e.g. origin/master",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch the wine repo remotes before computing merge-base",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    ge_root = Path(args.ge_root).resolve()
    out_dir = Path(args.output_dir).resolve()

    if not ge_root.exists():
        print(f"ERROR: ge root not found: {ge_root}", file=sys.stderr)
        return 1

    wine_dir = detect_wine_dir(ge_root)
    if not (wine_dir / ".git").exists():
        print(f"ERROR: wine source is not a git checkout: {wine_dir}", file=sys.stderr)
        return 1

    if args.fetch:
        print("Fetching wine remotes...")
        git(["fetch", "--all", "--tags", "--prune"], cwd=wine_dir)

    upstream_ref = args.upstream_ref or detect_default_upstream_ref(wine_dir)
    ge_wine_commit = git(["rev-parse", "HEAD"], cwd=wine_dir)
    base_commit = git(["merge-base", "HEAD", upstream_ref], cwd=wine_dir)

    if ge_wine_commit == base_commit:
        print("No GE-only Wine commits detected relative to upstream base.")
        return 0

    patch_dir = out_dir / "patches"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    patch_dir.mkdir(parents=True, exist_ok=True)

    git(
        [
            "format-patch",
            "--binary",
            "--full-index",
            "--zero-commit",
            "--output-directory",
            str(patch_dir),
            f"{base_commit}..HEAD",
        ],
        cwd=wine_dir,
    )

    patch_files = sorted(patch_dir.glob("*.patch"))
    ge_wrapper_commit = ""
    if (ge_root / ".git").exists() and ge_root != wine_dir:
        try:
            ge_wrapper_commit = git(["rev-parse", "HEAD"], cwd=ge_root)
        except subprocess.CalledProcessError:
            ge_wrapper_commit = ""

    counts = top_level_counts(wine_dir, base_commit)
    inventory = {
        "ge_root": str(ge_root),
        "wine_dir": str(wine_dir),
        "ge_wrapper_commit": ge_wrapper_commit,
        "ge_wine_commit": ge_wine_commit,
        "upstream_ref": upstream_ref,
        "base_commit": base_commit,
        "patch_count": len(patch_files),
        "top_level_file_counts": counts,
        "patch_files": [p.name for p in patch_files],
    }

    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        "# GE Wine Patch Inventory",
        "",
        f"- GE root: `{ge_root}`",
        f"- Wine tree: `{wine_dir}`",
        f"- GE wrapper commit: `{ge_wrapper_commit or 'n/a'}`",
        f"- GE wine commit: `{ge_wine_commit}`",
        f"- Upstream ref: `{upstream_ref}`",
        f"- Merge-base upstream commit: `{base_commit}`",
        f"- Patch count: `{len(patch_files)}`",
        "",
        "## Top-level file counts",
        "",
    ]
    for key, value in counts.items():
        summary_lines.append(f"- `{key}`: {value}")
    summary_lines.extend([
        "",
        "## Patch files",
        "",
    ])
    for path in patch_files:
        summary_lines.append(f"- `{path.name}`")

    (out_dir / "README.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Extracted {len(patch_files)} patch(es) to {patch_dir}")
    print(f"Inventory written to {out_dir / 'inventory.json'}")
    print(f"Summary written to {out_dir / 'README.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
