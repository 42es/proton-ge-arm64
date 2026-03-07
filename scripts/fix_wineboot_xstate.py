#!/usr/bin/env python3
"""
Fix missing initialize_xstate_features in the __aarch64__ branch of wineboot.c.

In ValveSoftware/wine proton_10.0, programs/wineboot/wineboot.c has:

  #if defined(__i386__) || defined(__x86_64__)
      static void initialize_xstate_features(...) { /* x86 impl */ }
  #elif defined(__aarch64__)
      static UINT64 read_tsc_frequency(void) { ... }   // <-- no xstate here!
  #else
      static void initialize_xstate_features(...) {}   // empty stub
      static UINT64 read_tsc_frequency(void) { return 0; }
  #endif

  ...
      initialize_xstate_features( data );  // always compiled, always called

When building as -target aarch64-windows PE, clang defines __aarch64__, so the
#elif branch is taken -- which provides read_tsc_frequency but NOT
initialize_xstate_features. The call at line ~539 then has no visible declaration:

  error: call to undeclared function 'initialize_xstate_features'

Fix: inject an empty initialize_xstate_features stub into the #elif __aarch64__
block, immediately before the existing read_tsc_frequency definition there.

Usage: fix_wineboot_xstate.py <wine-source-dir>
"""
import re
import sys
from pathlib import Path

WINEBOOT = "programs/wineboot/wineboot.c"

# The marker that uniquely identifies the start of the aarch64 branch
# (the read_tsc_frequency definition that's there but has no xstate companion).
AARCH64_BRANCH_MARKER = "#elif defined(__aarch64__)"

# What we inject - an empty stub matching the function signature used in the file
XSTATE_STUB = (
    "\nstatic void initialize_xstate_features( struct _KUSER_SHARED_DATA *data )\n"
    "{\n"
    "}\n"
)


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_wineboot_xstate.py <wine-source-dir>")
        sys.exit(1)

    wine_src = Path(sys.argv[1])
    target = wine_src / WINEBOOT

    if not target.exists():
        print(f"fix_wineboot_xstate: {WINEBOOT} not found, skipping")
        return

    text = target.read_text(encoding="utf-8", errors="replace")

    # Nothing to fix if the call isn't there
    if "initialize_xstate_features" not in text:
        print("fix_wineboot_xstate: call not found in wineboot.c, skipping")
        return

    # Already patched
    if XSTATE_STUB.strip() in text:
        print("fix_wineboot_xstate: aarch64 xstate stub already present, skipping")
        return

    # Find the #elif defined(__aarch64__) line
    idx = text.find(AARCH64_BRANCH_MARKER)
    if idx == -1:
        print("fix_wineboot_xstate: #elif __aarch64__ marker not found, skipping")
        return

    # Find the end of that line (insert after it)
    eol = text.find('\n', idx)
    if eol == -1:
        print("fix_wineboot_xstate: could not find newline after marker, skipping")
        return

    new_text = text[:eol + 1] + XSTATE_STUB + text[eol + 1:]
    target.write_text(new_text, encoding="utf-8")
    print("fix_wineboot_xstate: injected initialize_xstate_features stub into #elif __aarch64__ block")


if __name__ == "__main__":
    main()
