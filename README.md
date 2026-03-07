# GE-Proton ARM64 Experiments for Winlator

Experimental GE-Proton-style builds for Android ARM64, packaged as `.wcp` files for Winlator/GameNative testing. This track is split out from the bleeding-edge pipeline so GE-specific source selection, patches, and packaging changes can evolve independently.

## Getting a build

1. Head to [Releases](../../releases) and grab the latest `.wcp` file
2. Copy it to your Android device
3. Open Winlator or GameNative and import the package
4. Test it in a fresh container first

## What's inside

Each build includes:

- Wine for ARM64 Android (built with NDK r27d, targeting Android 9+)
- ARM64EC Windows PE DLLs for ARM Windows apps
- ARM64 and 32-bit (WoW64) PE DLLs
- A default Wine prefix (`prefixPack.txz`)

There are two package formats per build:

| File | For |
|------|-----|
| `.wcp` | Standard Winlator / GameNative |
| `.wcp.xz` | Winlator Cmod / Ludashi |

## Where the source comes from

This track is intended to move toward [GloriousEggroll/proton-ge-custom](https://github.com/GloriousEggroll/proton-ge-custom) as the Proton baseline, while still layering on the Android and ARM64EC pieces needed for Winlator/GameNative. The current scaffold is based on the existing ARM64 nightly pipeline and still needs GE-specific source and patch integration work.

## Build status

This folder is an experimental track. The workflow is intended for manual iteration first, not unattended production releases, until the GE source and patch stack are validated.

## Docs

- [WCP_STRUCTURE.md](docs/WCP_STRUCTURE.md) — how the `.wcp` format works
- [BUILD_REQUIREMENTS.md](docs/BUILD_REQUIREMENTS.md) — what you need to build locally
- [BUILD_ISSUES.md](docs/BUILD_ISSUES.md) — known issues and fixes
- [USER_GUIDE.md](docs/USER_GUIDE.md) — installation walkthrough
- [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — how to contribute or fork

## License

The scripts in this repo are MIT licensed. Wine itself is LGPL. See [LICENSE](LICENSE).
