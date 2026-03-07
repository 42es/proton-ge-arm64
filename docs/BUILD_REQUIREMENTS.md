# Build Requirements for Proton ARM64 Nightly Builds

## Architecture Context

Proton for Winlator is NOT standard desktop Proton. It is Wine built against the
**Android NDK** targeting ARM64 (aarch64). The reference build uses:
- Android NDK r27
- Target: Android API 28 (Android 9.0+)
- Interpreter: `/system/bin/linker64` (Android dynamic linker)

This means the build system is **Android NDK-based**, not the standard
Valve Steam Runtime SDK used for desktop Proton.

## Build Host Requirements

### Operating System
- Linux x86_64 (Ubuntu 20.04+ or Debian 11+ recommended)
- macOS with Docker is possible but untested
- Windows WSL2 is possible but adds overhead

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Docker or Podman | Latest | Container-based build isolation |
| Git | 2.x+ | Source checkout |
| Python 3 | 3.8+ | Build scripts |
| curl / wget | Any | Downloading dependencies |
| xz-utils | Any | Compressing prefixPack.txz |
| zstd | 1.4+ | Creating .wcp files |
| tar | GNU tar | Archiving |

### Disk Space

| Item | Space Required |
|------|---------------|
| Proton source (with submodules) | ~5-10 GB |
| Android NDK | ~2 GB |
| Build artifacts | ~15-20 GB |
| Final .wcp output | ~250 MB |
| **Total recommended** | **~40 GB free** |

### RAM
- Minimum: 8 GB
- Recommended: 16+ GB
- Parallel link jobs can spike to 4-8 GB

### CPU
- Build time on 8-core x86_64: ~3-6 hours
- ccache can reduce incremental builds to 30-60 minutes
- ARM64 native host would be faster but is not required (cross-compilation works)

## Build Approach: Android NDK Cross-Compilation

The correct approach for Winlator's Proton is:
1. Use the **Android NDK** (not Valve's Steam Runtime SDK)
2. Cross-compile Wine targeting `aarch64-linux-android`
3. The existing build system is likely Winlator's own fork

### Key Repository
The reference .wcp was built by K11MCH1. The relevant source is likely:
- https://github.com/brunodev85/winlator (Winlator source)
- https://github.com/K11MCH1/Winlator101 (reference builds)

**NOT** the standard `https://github.com/ValveSoftware/Proton` repo, which targets
the Steam Runtime (glibc x86_64/ARM64 desktop Linux).

## Valve's Proton ARM64 vs Winlator's Wine/Proton

| | Valve Proton ARM64 | Winlator Proton |
|-|-------------------|-----------------|
| Target OS | Linux ARM64 (desktop) | Android ARM64 |
| Libc | glibc | bionic (Android) |
| Linker | ld-linux-aarch64 | /system/bin/linker64 |
| Build SDK | Steam Runtime SDK | Android NDK |
| Use case | ARM64 Linux gaming | Android gaming via Winlator |

## Android NDK Setup

```bash
# Download NDK r27 (matches reference build)
NDK_VERSION="android-ndk-r27c"
curl -LO "https://dl.google.com/android/repository/${NDK_VERSION}-linux.zip"
unzip "${NDK_VERSION}-linux.zip"
export ANDROID_NDK_HOME="$(pwd)/${NDK_VERSION}"
export PATH="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH"

# Verify
aarch64-linux-android28-clang --version
```

## Cross-Compilation Toolchain

The NDK provides:
```
aarch64-linux-android28-clang      # C compiler
aarch64-linux-android28-clang++    # C++ compiler
llvm-ar                            # Archiver
llvm-strip                         # Strip tool
```

Configure flags for Wine cross-compilation to Android:
```bash
./configure \
  --host=aarch64-linux-android \
  --with-wine-tools=/path/to/wine-tools \
  TARGETCC="aarch64-linux-android28-clang" \
  TARGETCXX="aarch64-linux-android28-clang++" \
  ...
```

## Wine Source for Android Builds

The reference `.wcp` binary strings reveal exactly how it was built:
- **Wine version:** `wine-10.0` (stable release)
- **Build path:** `/home/endeavour/Documenti/SourceCodes/wine-arm64ec-10/`
- **Compiler:** Android NDK 27.0.12077973 (r27c), Clang 18.0.1
- **Winlator target path:** `/data/data/com.winlator.cmod/files/imagefs/usr/`

The builder applied arm64ec patches locally to Wine 10.0 — there is **no public fork**.
The closest available public source is the Wine GitHub mirror at the `wine-10.0` tag:

```bash
# Wine 10.0 stable (GitHub mirror of WineHQ)
git clone --depth=1 --branch wine-10.0 https://github.com/wine-mirror/wine wine-source

# For latest Wine development (wine-next branch):
git clone --depth=1 --branch wine-next https://github.com/wine-mirror/wine wine-source
```

**Important:** This is mainline Wine without Android/arm64ec patches. You will need
to apply arm64ec patches from the Wine mailing list or community sources before the
build will produce correct ARM64EC binaries for Winlator.

## GitHub Actions Considerations

### Standard Runners (ubuntu-latest)
- 2-core x86_64, 7 GB RAM, ~14 GB disk
- Disk is too small for full build (~40 GB needed)
- Job timeout: 6 hours (may not be enough)
- **Workaround:** Use a self-hosted runner or split build into cached stages

### Self-Hosted Runner (Recommended)
- Can be a VM, VPS, or physical machine
- Needs Linux x86_64 with 40+ GB disk, 8+ GB RAM
- No time limits

### Caching Strategy
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.ccache
      android-ndk-r27c/
    key: ${{ runner.os }}-ndk-r27c-${{ hashFiles('**/configure.ac') }}
```

## Known Blockers

1. **Valve's ARM64 SDK** (from spec) is for desktop ARM64 Linux, NOT Android. It cannot be used for Winlator builds.
2. **Wine source**: Must use a version with Android/Bionic patches. Mainline Wine does not build for Android out of the box.
3. **prefixPack.txz**: The default Wine prefix must be generated separately (Wine needs to run once to create it).
