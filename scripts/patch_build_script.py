#!/usr/bin/env python3
"""
Patches build-step-arm64ec.sh to use forgiving patch application for most
patches, but fail hard for critical test-bylaws patches required for runtime.

For test-bylaws patches we try, in order:
1) git apply with loose whitespace/context
2) git apply 3-way
3) GNU patch (fuzzy line-offset application)
4) reverse-check for already-applied
Then fail if none work.
"""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else 'build-scripts/build-step-arm64ec.sh'

with open(path) as f:
    txt = f.read()

txt = txt.replace(
    'git apply ./android/patches/$patch',
    'if [[ "$patch" == test-bylaws/* ]]; then '
    'git apply --ignore-whitespace -C1 ./android/patches/$patch'
    ' || git apply --3way --ignore-space-change ./android/patches/$patch'
    ' || patch -p1 --forward --batch --ignore-whitespace -i ./android/patches/$patch'
    ' || git apply --ignore-whitespace -C1 -R --check ./android/patches/$patch 2>/dev/null'
    ' && echo "ALREADY APPLIED (skipped): $patch"'
    ' || { echo "ERROR: critical patch failed: $patch"; exit 1; }; '
    'else '
    'git apply --ignore-whitespace -C1 ./android/patches/$patch 2>/dev/null'
    ' || git apply --ignore-whitespace -C1 -R --check ./android/patches/$patch 2>/dev/null'
    ' && echo "ALREADY APPLIED (skipped): $patch"'
    ' || echo "WARNING: $patch did not apply and is not already present"; '
    'fi'
)

with open(path, 'w') as f:
    f.write(txt)

print(f"Patched {path}")
