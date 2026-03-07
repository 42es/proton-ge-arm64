# Developer Guide: Proton ARM64 Nightly Build System

## Architecture Overview

```
                  GitHub Actions (cron: 2 AM UTC)
                         |
                         v
              +----------------------+
              |  Clone Wine source   |
              |  (Android fork)      |
              +----------------------+
                         |
                         v
              +----------------------+
              |  Download Android    |
              |  NDK r27c            |
              +----------------------+
                         |
                         v
              +----------------------+
              |  Build host tools    |
              |  (x86_64 wine-tools) |
              +----------------------+
                         |
                         v
              +----------------------+
              |  Cross-compile Wine  |
              |  for ARM64 Android   |
              +----------------------+
                         |
                         v
              +----------------------+
              |  Stage + Strip       |
              |  Add prefixPack.txz  |
              |  Generate profile.json|
              +----------------------+
                         |
                         v
              +----------------------+
              |  Package as .wcp     |
              |  (tar | zstd -19)    |
              +----------------------+
                         |
                         v
              +----------------------+
              |  GitHub Release      |
              |  Update latest.json  |
              +----------------------+
```

## Repository Structure

```
proton-arm64-nightlies/
├── .github/
│   └── workflows/
│       └── proton-nightly-build.yml  # CI/CD pipeline
├── scripts/
│   ├── create-proton-wcp.sh          # Core packaging script
│   ├── configure-arm64-build.sh      # Build configuration helper
│   ├── build-proton-arm64.sh         # Full automated build
│   ├── package-proton-wcp.sh         # High-level packaging pipeline
│   └── compare-builds.sh             # Build diff tool
├── docs/
│   ├── WCP_STRUCTURE.md              # .wcp format documentation
│   ├── BUILD_REQUIREMENTS.md         # What you need to build
│   ├── BUILD_ISSUES.md               # Known problems + solutions
│   ├── USER_GUIDE.md                 # End-user documentation
│   └── DEVELOPER_GUIDE.md            # This file
├── reference/
│   └── extracted/                    # Extracted reference .wcp (git-ignored)
├── output/                           # Build outputs (git-ignored)
├── README.md
├── LICENSE
└── latest.json                       # Updated by CI with each build
```

## Key Technical Decisions

### 1. Zstandard compression (not XZ)

The .wcp format uses **Zstandard** compression, not XZ. This was discovered by
inspecting the reference build's magic bytes. The spec assumed XZ; this was wrong.

Always detect format with: `file <name>.wcp`

### 2. profile.json type is "Proton"

The `type` field must be `"Proton"` (not `"Wine"`) for Winlator to recognize the
package correctly and look for the `proton` configuration block.

### 3. Android NDK, not Valve's Steam Runtime SDK

Winlator's Wine targets Android/bionic. Valve's Proton targets desktop Linux/glibc.
These are incompatible. The Android NDK r27 is required.

Reference binary confirms:
```
interpreter /system/bin/linker64, for Android 28, built by NDK r27
```

### 4. Wine source needs Android patches

Stock Wine (winehq.org) does not build for Android without patches. Use:
- Winlator's Wine fork (brunodev85/winlator or their Wine submodule)
- Or apply Android compatibility patches to mainline Wine

## Local Build Setup

### Prerequisites

```bash
# Ubuntu 22.04
sudo apt-get install -y build-essential flex bison python3-pip \
  libgnutls28-dev libunwind-dev pkg-config ccache zstd git xz-utils
pip3 install zstandard
```

### Download Android NDK

```bash
curl -LO https://dl.google.com/android/repository/android-ndk-r27c-linux.zip
unzip android-ndk-r27c-linux.zip
export ANDROID_NDK_HOME="$(pwd)/android-ndk-r27c"
```

### Clone Wine Source

```bash
# Use Winlator's patched Wine fork
git clone --depth=1 https://github.com/brunodev85/winlator wine-source
# (Check if they have a separate Wine submodule - use that if so)
```

### Run the Build

```bash
./scripts/build-proton-arm64.sh \
  --ndk-path "$ANDROID_NDK_HOME" \
  --source-dir ./wine-source \
  --build-dir ./wine-build \
  --jobs $(nproc)
```

### Package Only (if you already have a built Wine install)

```bash
./scripts/package-proton-wcp.sh ./wine-install ./output
```

## How to Modify/Customize Builds

### Adding Patches

Place patch files in `patches/` and apply them in `build-proton-arm64.sh`
before the configure step:

```bash
# In build-proton-arm64.sh, before Step 1:
for patch in "$SCRIPT_DIR/../patches/"*.patch; do
    git -C "$SOURCE_DIR" apply "$patch"
done
```

### Changing Wine Source

Edit the `WINE_SOURCE_REPO` environment variable in the GitHub Actions workflow,
or pass `--source-dir` to `build-proton-arm64.sh`.

### Adding DXVK / vkd3d-proton

After building Wine, copy DXVK ARM64 builds into the install directory:
```bash
# DXVK needs to be in lib/wine/aarch64-windows/ (as .dll files)
# and overrides set in the prefix registry
cp dxvk-arm64/*.dll wine-install/lib/wine/aarch64-windows/
```

### Changing Compression Level

In `create-proton-wcp.sh`, the zstd level is `-19` (maximum). For faster builds:
```bash
zstd -T0 -9 ...   # Level 9: faster, slightly larger
zstd -T0 -19 ...  # Level 19: slower, smallest size (default)
```

## Testing Procedures

### 1. Verify .wcp Integrity

```bash
# Check it's valid zstd + tar
file output/proton-10-arm64ec-nightly-*.wcp

# Extract and check structure
python3 -c "
import zstandard, tarfile
with open('output/proton-10-arm64ec-nightly-*.wcp', 'rb') as f:
    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_reader(f) as r:
        with tarfile.open(fileobj=r, mode='r|') as tf:
            names = [m.name for m in tf]
print('Files found:', len(names))
print('Has profile.json:', any('profile.json' in n for n in names))
print('Has bin/wine:', any('bin/wine' == n.lstrip('./') for n in names))
"
```

### 2. Compare with Reference

```bash
./scripts/compare-builds.sh \
  reference/Proton-10-arm64ec-controller-fix.wcp \
  output/proton-10-arm64ec-nightly-*.wcp
```

### 3. Verify ARM64 Binaries

After extraction:
```bash
file extracted/bin/wine
# Expected: ELF 64-bit LSB pie executable, ARM aarch64, for Android 28
```

### 4. Validate profile.json

```bash
python3 -c "import json; json.load(open('extracted/profile.json')); print('Valid JSON')"
```

## Troubleshooting

### Build fails: "No such file or directory" for compiler

NDK path is wrong or toolchain not installed.
```bash
ls $ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android28-clang
```

### Build fails: missing Wine headers / submodules

If using Winlator's repo, it may have submodules:
```bash
git -C wine-source submodule update --init --recursive
```

### GitHub Actions: disk full

Cleanup step isn't freeing enough space. Options:
1. Remove more packages from cleanup step
2. Use self-hosted runner
3. Split build into cached stages

### .wcp works on one Winlator version but not another

Check the Winlator Cmod version requirements. The `profile.json` format may
vary between Winlator versions. Always test against the target Winlator version.

## Contributing

1. Fork this repository
2. Make changes on a feature branch
3. Test locally with `./scripts/build-proton-arm64.sh --help`
4. Submit a pull request with a description of the change
5. CI will verify the build pipeline is valid

## Updating When Valve Updates Proton

The Wine source is separate from Valve's Proton. To track Wine upstream:
1. Update `WINE_REF` in the workflow or source clone step
2. Check if Android patches still apply cleanly
3. Test a build and compare with reference
4. Update version number in `profile.json` generation
