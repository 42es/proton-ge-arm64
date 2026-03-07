# Known Build Issues and Solutions

## Issue 1: .wcp is Zstandard, not XZ

**Symptom:** `xz -d file.wcp` fails with "not an xz file"

**Root cause:** The spec assumed XZ compression but the actual format is Zstandard.

**Detection:**
```bash
file Proton-10-arm64ec-controller-fix.wcp
# Output: Zstandard compressed data (v0.8+), Dictionary ID: None
```

**Solution:** Use `zstd` to decompress, or use Python's `zstandard` library.

```bash
# Install zstd on Ubuntu/Debian
sudo apt-get install zstd

# Decompress
zstd -d file.wcp -o file.tar
tar -xf file.tar
```

---

## Issue 2: profile.json type is "Proton" not "Wine"

**Symptom:** Package not recognized by Winlator or shows as wrong type.

**Root cause:** The spec assumed `"type": "Wine"` but the correct value is `"type": "Proton"`.

**Solution:** Always use:
```json
{
  "type": "Proton",
  ...
  "proton": {
    "binPath": "bin",
    "libPath": "lib",
    "prefixPack": "prefixPack.txz"
  }
}
```

---

## Issue 3: Valve's ARM64 SDK Cannot Build Winlator Proton

**Symptom:** Build fails with linker errors referencing glibc symbols.

**Root cause:** Valve's `proton/sniper/sdk/arm64/llvm` targets desktop Linux ARM64 (glibc).
Winlator requires Android (bionic) ARM64 builds.

**Solution:** Use the Android NDK r27 instead. The reference binary shows:
```
interpreter /system/bin/linker64, for Android 28, built by NDK r27
```

---

## Issue 4: Wine Mainline Doesn't Build for Android

**Symptom:** Configure fails with missing headers or link errors against bionic.

**Root cause:** Wine mainline targets glibc Linux. Building for Android/bionic requires patches.

**Solution:** Use Winlator's patched Wine source or apply Android patches from:
- Winlator source repo (brunodev85/winlator)
- Wine-Android project patches

---

## Issue 5: No zstd Binary on Windows

**Symptom:** Cannot create .wcp files on Windows without zstd binary.

**Solution:** Use Python's `zstandard` library:
```bash
pip install zstandard
python create-proton-wcp.py <input_dir> <output.wcp>
```

The `create-proton-wcp.sh` script handles this automatically by detecting whether
`zstd` binary is available and falling back to Python.

---

## Issue 6: GitHub Actions Disk Space

**Symptom:** Build fails with "No space left on device"

**Root cause:** Standard runners have ~14 GB disk; Proton build needs ~40 GB.

**Mitigation options:**
1. Free disk space before build:
   ```yaml
   - name: Free disk space
     run: |
       sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc
       df -h
   ```
2. Use a self-hosted runner with adequate disk
3. Use ccache and cache build artifacts between runs

---

## Issue 7: Build Timeout on GitHub Actions

**Symptom:** Job killed after 6 hours.

**Mitigation:**
- Use ccache (saves 50-70% of build time after first run)
- Split build into multiple jobs with artifact passing
- Use self-hosted runner (no time limit)
- Build only changed components

---

## Issue 8: prefixPack.txz Generation

**Symptom:** Missing default Wine prefix; Winlator shows errors on first launch.

**Root cause:** `prefixPack.txz` is not a build artifact - it's a pre-initialized Wine prefix.

**Solution:**
1. Reuse the `prefixPack.txz` from the reference build (it rarely changes)
2. Or generate a fresh one by running `wineboot --init` with the new Wine build
   and archiving `~/.wine/` as `prefixPack.txz`
