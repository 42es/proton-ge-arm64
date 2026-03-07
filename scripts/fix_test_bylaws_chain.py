#!/usr/bin/env python3
"""
Apply and verify additional BYLAWS patch chain pieces that commonly drift on
bleeding-edge and can cause runtime hangs if partially missing.

Usage: fix_test_bylaws_chain.py <wine-source-dir>
Script rev: 2026-03-07-dedupefix-v2
"""
import os
import re
import subprocess
import sys


PATCHES = [
    "dlls_ntdll_loader_c.patch",
    "dlls_ntdll_unwind_h.patch",
    "include_winnt_h.patch",
    "dlls_ntdll_ntdll_misc_h.patch",
    "dlls_ntdll_ntdll_spec.patch",
    "dlls_ntdll_signal_arm64_c.patch",
    "dlls_ntdll_signal_arm64ec_c.patch",
    "dlls_ntdll_signal_x86_64_c.patch",
    "dlls_wow64_syscall_c.patch",
    "dlls_wow64_wow64_spec.patch",
    "include_winternl_h.patch",
    "tools_makedep_c.patch",
]

# relative file -> markers that must all be present after patching
REQUIRED_MARKERS = {
    "dlls/ntdll/unwind.h": [
        "CONTEXT_ARM64_FEX_YMMSTATE",
    ],
    "include/winnt.h": [
        "CONTEXT_ARM64_FEX_YMMSTATE",
    ],
    "dlls/ntdll/loader.c": [
        "pWow64SuspendLocalThread",
        "GET_PTR( Wow64SuspendLocalThread )",
    ],
    "dlls/ntdll/ntdll_misc.h": [
        "pWow64SuspendLocalThread",
    ],
    "dlls/ntdll/ntdll.spec": [
        "RtlWow64SuspendThread",
    ],
    "dlls/ntdll/signal_arm64.c": [
        "RtlWow64SuspendThread",
    ],
    "dlls/ntdll/signal_arm64ec.c": [
        "RtlWow64SuspendThread",
    ],
    "dlls/ntdll/signal_x86_64.c": [
        "RtlWow64SuspendThread",
    ],
    "dlls/wow64/syscall.c": [
        "Wow64SuspendLocalThread",
    ],
    "dlls/wow64/wow64.spec": [
        "Wow64SuspendLocalThread",
    ],
    "include/winternl.h": [
        "THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE",
        "RtlWow64SuspendThread",
    ],
    "tools/makedep.c": [
        "arch_install_dirs[arch] = \"$(libdir)/wine/aarch64-windows/\";",
        "output_symlink_rule(",
    ],
}


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def read_text(path):
    with open(path, errors="replace") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w") as f:
        f.write(text)


def apply_once(text, old, new):
    if new in text:
        return text, True, False
    if old not in text:
        return text, False, False
    return text.replace(old, new, 1), True, True


def insert_after_anchor(text, marker, block, anchors):
    if marker in text:
        return text, True, False
    for a in anchors:
        idx = text.find(a)
        if idx >= 0:
            pos = idx + len(a)
            return text[:pos] + block + text[pos:], True, True
    return text, False, False


def find_function_block(text, start_idx):
    brace = text.find("{", start_idx)
    if brace < 0:
        return -1, -1

    depth = 0
    i = brace
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(text) and text[end] in " \t\r\n":
                    end += 1
                return start_idx, end
        i += 1

    return -1, -1


def find_definition_starts(text, func_name):
    # Find candidate occurrences by function-name token, then keep only entries
    # that map to a real brace-delimited block starting from the containing line.
    name_pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
    starts = []
    for m in name_pattern.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        b0, b1 = find_function_block(text, line_start)
        if b0 == line_start and b1 > b0:
            starts.append(line_start)
    return starts


def dedupe_function(text, func_name):
    starts = find_definition_starts(text, func_name)

    if len(starts) <= 1:
        return text, 0

    removed = 0
    # Keep first definition, remove later duplicates.
    for s in reversed(starts[1:]):
        b0, b1 = find_function_block(text, s)
        if b0 >= 0 and b1 > b0:
            text = text[:b0] + text[b1:]
            removed += 1

    return text, removed


def normalize_signal_duplicates(wine_src):
    notes = []
    files = [
        "dlls/ntdll/signal_arm64.c",
        "dlls/ntdll/signal_arm64ec.c",
        "dlls/ntdll/signal_x86_64.c",
    ]
    signatures = [
        "suspend_remote_breakin",
        "RtlWow64SuspendThread",
    ]

    for rel in files:
        path = os.path.join(wine_src, rel)
        if not os.path.exists(path):
            continue

        txt = read_text(path)
        total = 0
        for sig in signatures:
            txt, n = dedupe_function(txt, sig)
            total += n

        if total:
            write_text(path, txt)
            notes.append(f"FIXED: {rel} removed {total} duplicate suspend definition(s)")

    return notes


def patch_already_present(wine_src, patch_name):
    checks = {
        "dlls_ntdll_signal_arm64_c.patch": ("dlls/ntdll/signal_arm64.c", ["suspend_remote_breakin", "RtlWow64SuspendThread"]),
        "dlls_ntdll_signal_arm64ec_c.patch": ("dlls/ntdll/signal_arm64ec.c", ["RtlWow64SuspendThread"]),
        "dlls_ntdll_signal_x86_64_c.patch": ("dlls/ntdll/signal_x86_64.c", ["RtlWow64SuspendThread"]),
    }
    if patch_name not in checks:
        return False

    rel, func_names = checks[patch_name]
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return False

    txt = read_text(path)
    for func_name in func_names:
        if len(find_definition_starts(txt, func_name)) < 1:
            return False
    return True


def try_apply_patch(wine_src, patch_path):
    attempts = [
        ["git", "-C", wine_src, "apply", "--ignore-whitespace", "-C1", patch_path],
        ["git", "-C", wine_src, "apply", "--3way", "--ignore-space-change", patch_path],
        ["patch", "-d", wine_src, "-p1", "--forward", "--batch", "--ignore-whitespace", "-i", patch_path],
    ]

    for cmd in attempts:
        rc, out = run(cmd, cwd=None)
        if rc == 0:
            return True, out

    # already-applied check
    rc, out = run(
        ["git", "-C", wine_src, "apply", "--ignore-whitespace", "-C1", "-R", "--check", patch_path],
        cwd=None,
    )
    if rc == 0:
        return True, "already applied"

    return False, out


def fallback_fix_winnt(wine_src):
    rel = "include/winnt.h"
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return [f"MISSING: {rel}"]

    txt = read_text(path)
    notes = []

    replacements = [
        (
            "#define XSTATE_MASK_GSSE                    (1 << XSTATE_GSSE)\n",
            "#define XSTATE_MASK_GSSE                    (1 << XSTATE_GSSE)\n\n"
            "#define XSTATE_ARM64_SVE 2\n\n"
            "#define XSTATE_MASK_ARM64_SVE (1 << XSTATE_ARM64_SVE)\n",
            "XSTATE_ARM64_SVE",
        ),
        (
            "XSAVE_AREA_HEADER, *PXSAVE_AREA_HEADER;\n",
            "XSAVE_AREA_HEADER, *PXSAVE_AREA_HEADER;\n\n"
            "typedef struct _XSAVE_ARM64_SVE_HEADER {\n"
            "    ULONG VectorLength;\n"
            "    ULONG VectorRegisterOffset;\n"
            "    ULONG PredicateRegisterOffset;\n"
            "    ULONG Reserved[5];\n"
            "} XSAVE_ARM64_SVE_HEADER, *PXSAVE_ARM64_SVE_HEADER;\n",
            "XSAVE_ARM64_SVE_HEADER",
        ),
        (
            "#define CONTEXT_ARM64_X18       (CONTEXT_ARM64 | 0x00000010)\n",
            "#define CONTEXT_ARM64_X18       (CONTEXT_ARM64 | 0x00000010)\n"
            "#define CONTEXT_ARM64_XSTATE    (CONTEXT_ARM64 | 0x00000020)\n"
            "#define CONTEXT_ARM64_FEX_YMMSTATE   (CONTEXT_ARM64 | 0x00000040)\n",
            "CONTEXT_ARM64_FEX_YMMSTATE",
        ),
    ]

    for old, new, marker in replacements:
        if marker in txt:
            continue
        txt2, ok, _ = apply_once(txt, old, new)
        if ok:
            txt = txt2
            notes.append(f"FIXED: {rel} add {marker}")
        else:
            notes.append(f"WARN: {rel} could not place {marker}")

    write_text(path, txt)
    return notes


def fallback_fix_unwind(wine_src):
    rel = "dlls/ntdll/unwind.h"
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return [f"MISSING: {rel}"]

    txt = read_text(path)
    notes = []

    replacements = [
        (
            "    if (flags & CONTEXT_AMD64_FLOATING_POINT) ret |= CONTEXT_ARM64_FLOATING_POINT;\n",
            "    if (flags & CONTEXT_AMD64_FLOATING_POINT) ret |= CONTEXT_ARM64_FLOATING_POINT;\n"
            "    if (flags & CONTEXT_AMD64_XSTATE) ret |= CONTEXT_ARM64_FEX_YMMSTATE;\n",
            "if (flags & CONTEXT_AMD64_XSTATE) ret |= CONTEXT_ARM64_FEX_YMMSTATE;",
        ),
        (
            "    if (flags & CONTEXT_ARM64_FLOATING_POINT) ret |= CONTEXT_AMD64_FLOATING_POINT;\n",
            "    if (flags & CONTEXT_ARM64_FLOATING_POINT) ret |= CONTEXT_AMD64_FLOATING_POINT;\n"
            "    if (flags & CONTEXT_ARM64_FEX_YMMSTATE) ret |= CONTEXT_AMD64_XSTATE;\n",
            "if (flags & CONTEXT_ARM64_FEX_YMMSTATE) ret |= CONTEXT_AMD64_XSTATE;",
        ),
        (
            "    arm_ctx->Fpcr = fpcsr;\n    arm_ctx->Fpsr = fpcsr >> 32;\n",
            "    arm_ctx->Fpcr = fpcsr;\n    arm_ctx->Fpsr = fpcsr >> 32;\n\n"
            "    if ((ec_ctx->ContextFlags & CONTEXT_AMD64_XSTATE) == CONTEXT_AMD64_XSTATE)\n"
            "    {\n"
            "        CONTEXT_EX *ec_xctx = (CONTEXT_EX *)(ec_ctx + 1);\n"
            "        YMMCONTEXT *ec_ymm = RtlLocateExtendedFeature( ec_xctx, XSTATE_AVX, NULL );\n"
            "        memcpy( arm_ctx->V + 16, ec_ymm, sizeof(*ec_ymm) );\n"
            "    }\n",
            "memcpy( arm_ctx->V + 16, ec_ymm, sizeof(*ec_ymm) );",
        ),
        (
            "    memcpy( ec_ctx->V, arm_ctx->V, sizeof(ec_ctx->V) );\n",
            "    memcpy( ec_ctx->V, arm_ctx->V, sizeof(ec_ctx->V) );\n\n"
            "    if ((arm_ctx->ContextFlags & CONTEXT_ARM64_FEX_YMMSTATE) == CONTEXT_ARM64_FEX_YMMSTATE)\n"
            "    {\n"
            "        CONTEXT_EX *ec_xctx = (CONTEXT_EX *)(ec_ctx + 1);\n"
            "        YMMCONTEXT *ec_ymm = RtlLocateExtendedFeature( ec_xctx, XSTATE_AVX, NULL );\n"
            "        memcpy( ec_ymm, arm_ctx->V + 16, sizeof(*ec_ymm) );\n"
            "    }\n",
            "memcpy( ec_ymm, arm_ctx->V + 16, sizeof(*ec_ymm) );",
        ),
    ]

    for old, new, marker in replacements:
        if marker in txt:
            continue
        txt2, ok, _ = apply_once(txt, old, new)
        if ok:
            txt = txt2
            notes.append(f"FIXED: {rel} add {marker}")
        else:
            notes.append(f"WARN: {rel} could not place {marker}")

    write_text(path, txt)
    return notes


def fallback_fix_winternl(wine_src):
    rel = "include/winternl.h"
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return [f"MISSING: {rel}"]

    txt = read_text(path)
    notes = []

    if "THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE" not in txt:
        old = "#define THREAD_CREATE_FLAGS_SKIP_LOADER_INIT      0x00000100"
        new = (
            "#define THREAD_CREATE_FLAGS_SKIP_LOADER_INIT      0x00000100\n"
            "#define THREAD_CREATE_FLAGS_BYPASS_PROCESS_FREEZE 0x00000400"
        )
        txt2, ok, _ = apply_once(txt, old, new)
        if ok:
            txt = txt2
            notes.append(f"FIXED: {rel} add BYPASS_PROCESS_FREEZE define")
        else:
            notes.append(f"WARN: {rel} could not place BYPASS_PROCESS_FREEZE define")

    if "RtlWow64SuspendThread" not in txt:
        txt2, ok, _ = insert_after_anchor(
            txt,
            "RtlWow64SuspendThread",
            "NTSTATUS    WINAPI RtlWow64SuspendThread(HANDLE, PULONG);\n",
            [
                "NTSTATUS    WINAPI RtlWow64GetThreadContext(HANDLE, WOW64_CONTEXT *, I386_CONTEXT *);\n",
                "NTSTATUS    WINAPI RtlWow64SetThreadContext(HANDLE, const WOW64_CONTEXT *, const I386_CONTEXT *);\n",
            ],
        )
        if ok:
            txt = txt2
            notes.append(f"FIXED: {rel} add RtlWow64SuspendThread prototype")
        else:
            notes.append(f"WARN: {rel} could not place RtlWow64SuspendThread prototype")

    write_text(path, txt)
    return notes


def fallback_fix_signal_file(wine_src, rel):
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return [f"MISSING: {rel}"]

    txt = read_text(path)
    notes = []

    if "RtlWow64SuspendThread" not in txt:
        txt2, ok, _ = apply_once(txt, "NtSuspendThread(", "RtlWow64SuspendThread(")
        if ok:
            txt = txt2
            notes.append(f"FIXED: {rel} swap NtSuspendThread -> RtlWow64SuspendThread")
        else:
            notes.append(f"WARN: {rel} missing both marker and replace anchor")

    write_text(path, txt)
    return notes


def fallback_fix_wow64_syscall(wine_src):
    rel = "dlls/wow64/syscall.c"
    path = os.path.join(wine_src, rel)
    if not os.path.exists(path):
        return [f"MISSING: {rel}"]

    txt = read_text(path)
    notes = []

    if "Wow64SuspendLocalThread" not in txt:
        block = (
            "\n\n/**********************************************************************\n"
            " *           Wow64SuspendLocalThread  (wow64.@)\n"
            " */\n"
            "NTSTATUS WINAPI Wow64SuspendLocalThread( HANDLE thread, ULONG *count )\n"
            "{\n"
            "    return RtlWow64SuspendThread( thread, count );\n"
            "}\n"
        )
        txt += block
        notes.append(f"FIXED: {rel} add Wow64SuspendLocalThread implementation")

    write_text(path, txt)
    return notes


def apply_fallbacks(wine_src, failed_patch_names):
    notes = []

    if "include_winnt_h.patch" in failed_patch_names:
        notes.extend(fallback_fix_winnt(wine_src))

    if "dlls_ntdll_unwind_h.patch" in failed_patch_names:
        notes.extend(fallback_fix_unwind(wine_src))

    if "include_winternl_h.patch" in failed_patch_names:
        notes.extend(fallback_fix_winternl(wine_src))

    if "dlls_wow64_syscall_c.patch" in failed_patch_names:
        notes.extend(fallback_fix_wow64_syscall(wine_src))

    if "dlls_ntdll_signal_arm64_c.patch" in failed_patch_names:
        notes.extend(fallback_fix_signal_file(wine_src, "dlls/ntdll/signal_arm64.c"))

    if "dlls_ntdll_signal_arm64ec_c.patch" in failed_patch_names:
        notes.extend(fallback_fix_signal_file(wine_src, "dlls/ntdll/signal_arm64ec.c"))

    if "dlls_ntdll_signal_x86_64_c.patch" in failed_patch_names:
        notes.extend(fallback_fix_signal_file(wine_src, "dlls/ntdll/signal_x86_64.c"))

    return notes


def verify(wine_src):
    ok = True
    for rel, markers in REQUIRED_MARKERS.items():
        path = os.path.join(wine_src, rel)
        if not os.path.exists(path):
            print(f"VERIFY FAIL: missing file {rel}")
            ok = False
            continue

        txt = read_text(path)
        for m in markers:
            if m not in txt:
                print(f"VERIFY FAIL: marker '{m}' missing in {rel}")
                ok = False

    duplicate_checks = {
        "dlls/ntdll/signal_arm64.c": [
            "suspend_remote_breakin",
            "RtlWow64SuspendThread",
        ],
        "dlls/ntdll/signal_arm64ec.c": [
            "suspend_remote_breakin",
            "RtlWow64SuspendThread",
        ],
        "dlls/ntdll/signal_x86_64.c": [
            "suspend_remote_breakin",
            "RtlWow64SuspendThread",
        ],
    }

    for rel, func_names in duplicate_checks.items():
        path = os.path.join(wine_src, rel)
        if not os.path.exists(path):
            continue

        txt = read_text(path)
        for func_name in func_names:
            count = len(find_definition_starts(txt, func_name))
            if count > 1:
                print(f"VERIFY FAIL: duplicate definition of '{func_name}' present {count} times in {rel}")
                ok = False

    return ok


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_test_bylaws_chain.py <wine-source-dir>")
        return 1

    wine_src = os.path.abspath(sys.argv[1])
    print(f"fix_test_bylaws_chain: rev=2026-03-07-dedupefix-v2 wine_src={wine_src}")
    patch_dir = os.path.join(wine_src, "android", "patches", "test-bylaws")

    if not os.path.isdir(patch_dir):
        print(f"ERROR: patch dir not found: {patch_dir}")
        return 2

    had_hard_errors = False
    failed = []

    for name in PATCHES:
        p = os.path.join(patch_dir, name)
        if not os.path.exists(p):
            print(f"ERROR: missing patch {name}")
            had_hard_errors = True
            continue

        if patch_already_present(wine_src, name):
            print(f"BYLAWS OK: {name} (pre-existing definitions)")
            continue
        ok, info = try_apply_patch(wine_src, p)
        if ok:
            print(f"BYLAWS OK: {name}")
        else:
            print(f"BYLAWS DRIFT: {name}")
            print(info.strip())
            failed.append(name)

    if failed:
        print("Applying drift fallbacks for failed patches...")
        for n in apply_fallbacks(wine_src, set(failed)):
            print(f"  {n}")


    verified = verify(wine_src)

    if had_hard_errors or not verified:
        print("fix_test_bylaws_chain: FAILED")
        return 3

    print("fix_test_bylaws_chain: success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


