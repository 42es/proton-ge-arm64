# User Guide: Proton 10 ARM64 Nightly Builds for Winlator

## What Are These Builds?

These are nightly builds of **Proton 10** (a Wine-based compatibility layer)
compiled for **ARM64 Android** devices. They let you run Windows games on
Android through Winlator Cmod.

Unlike official Proton (which targets desktop Linux), these builds target
Android's native runtime (bionic/NDK), enabling use on Android devices
without desktop Linux dependencies.

## Requirements

- Android device with ARM64 processor
- Winlator Cmod (latest version recommended)
- ~500 MB free storage for the .wcp file
- ~2-3 GB free storage for the installed Wine environment

## How to Download

### Latest Nightly

1. Go to the **Releases** page of this repository
2. Find the latest release tagged `nightly-YYYYMMDD-HASH`
3. Download the `.wcp` file (e.g., `proton-10-arm64ec-nightly-20260305-abc1234.wcp`)
4. Download the `.sha256` file to verify integrity

### Verify Download (Optional but Recommended)

```bash
# On Linux/Mac:
sha256sum -c proton-10-arm64ec-nightly-20260305-abc1234.wcp.sha256

# On Windows (PowerShell):
Get-FileHash proton-10-arm64ec-nightly-20260305-abc1234.wcp -Algorithm SHA256
```

## How to Install in Winlator Cmod

### Method 1: Import via Winlator UI (Recommended)

1. Copy the `.wcp` file to your Android device (internal storage or SD card)
2. Open **Winlator Cmod**
3. Tap the **menu** icon (three lines) or go to **Settings**
4. Navigate to **Wine Version** or **Wine Configuration**
5. Tap **Import** or the **+** button
6. Browse to and select your `.wcp` file
7. Wait for the import to complete (may take 1-2 minutes)
8. The new version will appear in the Wine version list

### Method 2: Manual Installation

If the UI import fails:
1. Use a file manager to navigate to Winlator's data directory
2. Place the `.wcp` in the appropriate wines folder
3. Restart Winlator

## Selecting the Nightly Build

After installation:
1. Open Winlator Cmod
2. Edit your container or create a new one
3. In container settings, find **Wine Version**
4. Select `10-arm64ec-nightly-YYYYMMDD-HASH` from the dropdown
5. Save and launch

## Known Issues

### Compared to Proton-10-arm64ec-controller-fix.wcp (Reference)

| Feature | Reference Build | Nightly Build |
|---------|---------------|---------------|
| Controller fix patch | Included | May not be included |
| Stability | Tested | Bleeding edge, may have regressions |
| Update frequency | Manual | Daily |
| Source | K11MCH1 | Automated build |

### Common Problems

**"Wine version not appearing after import"**
- Ensure the file downloaded completely (check SHA256)
- Try restarting Winlator after import
- Check available storage space

**"Game crashes immediately"**
- Nightly builds may have regressions; try the reference build
- Check Winlator's log output for errors
- Report the issue with the specific nightly build date

**"Import fails or errors"**
- Ensure you're using Winlator Cmod, not the base Winlator
- The `.wcp` format requires a compatible Winlator version

## How to Report Problems

1. Open an **Issue** on this repository
2. Include:
   - The nightly build date/hash (from the filename)
   - Your device model and Android version
   - Winlator Cmod version
   - The game or app you're trying to run
   - Error messages or logs from Winlator

## Rollback to a Previous Version

All nightly builds are kept in GitHub Releases. To go back:
1. Open **Releases** in this repository
2. Find the date you want to roll back to
3. Download and install that `.wcp` file
4. Select it in Winlator's container settings

## Comparison: Nightly vs Reference Build

The reference build (`Proton-10-arm64ec-controller-fix.wcp` by K11MCH1) is:
- Manually tested and more stable
- May lag behind the latest Wine development
- Includes specific controller compatibility fixes

The nightly builds are:
- Automatically built from the latest source
- Potentially include the newest Wine improvements and bug fixes
- May introduce new bugs (bleeding edge)
- Good for testing specific Wine improvements

**Recommendation:** Use the reference build for stability. Switch to nightlies
to test specific bugs that may be fixed in newer Wine.
