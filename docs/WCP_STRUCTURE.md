# .wcp File Format Documentation

## Overview

A `.wcp` (Wine/Proton Container Package) file is a **Zstandard-compressed tar archive**.

**Important correction from spec:** The format is NOT XZ-compressed. It is Zstandard (zstd), detectable by magic bytes `0xFD2FB528`.

## Archive Format

```
.wcp file = tar archive compressed with Zstandard (zstd)
```

To inspect: `file Proton-10-arm64ec-controller-fix.wcp`
Output: `Zstandard compressed data (v0.8+), Dictionary ID: None`

## Extraction

```bash
# Method 1: Python (works on Windows without zstd binary)
python3 -c "
import zstandard, tarfile
with open('file.wcp', 'rb') as f:
    dctx = zstandard.ZstdDecompressor()
    with dctx.stream_reader(f) as reader:
        with tarfile.open(fileobj=reader, mode='r|') as tf:
            tf.extractall('output_dir')
"

# Method 2: If zstd binary is available
zstd -d file.wcp -o file.tar
tar -xf file.tar

# Method 3: tar with zstd support (GNU tar >= 1.31)
tar --zstd -xf file.wcp
```

## Directory Structure (Proton type)

Verified from `Proton-10-arm64ec-controller-fix.wcp` (222 MB compressed, 1436 MB uncompressed):

```
./
├── profile.json              (246 bytes) - Package metadata
├── prefixPack.txz            (23 MB)     - Default Wine prefix, XZ-compressed tar
├── bin/                      (3.6 MB)    - Native ARM64 executables + shell wrappers
│   ├── wine                  ELF ARM64 aarch64 (Android NDK r27)
│   ├── wine-preloader        ELF ARM64 aarch64, statically linked
│   ├── wineserver            ELF ARM64 aarch64 (Android NDK r27), 3.5 MB
│   ├── msidb                 shell wrapper script (1973 bytes)
│   ├── msiexec               shell wrapper script
│   ├── notepad               shell wrapper script
│   ├── regedit               shell wrapper script
│   ├── regsvr32              shell wrapper script
│   ├── wineboot              shell wrapper script
│   ├── winecfg               shell wrapper script
│   ├── wineconsole           shell wrapper script
│   ├── winedbg               shell wrapper script
│   ├── winefile              shell wrapper script
│   ├── winemine              shell wrapper script
│   └── winepath              shell wrapper script
├── lib/                      (1.4 GB)    - Wine libraries
│   └── wine/
│       ├── aarch64-unix/     (32 .so files) - Native ARM64 Unix shared objects
│       ├── aarch64-windows/  (755 files)    - ARM64 PE DLLs/EXEs for Wine
│       └── i386-windows/     (814 files)    - 32-bit x86 PE DLLs/EXEs for Wine
└── share/                    (12 MB)     - Wine data files
    └── wine/
        ├── fonts/            (56 files)  - Wine font files
        ├── nls/              (76 files)  - National Language Support data
        └── wine.inf          (163 KB)    - Wine INF setup file
```

## Binary Architecture Details

| Binary | Architecture | Notes |
|--------|-------------|-------|
| `bin/wine` | ELF ARM64 aarch64 | Android NDK r27, dynamically linked, interpreter `/system/bin/linker64` |
| `bin/wineserver` | ELF ARM64 aarch64 | Android NDK r27, 3.5 MB |
| `bin/wine-preloader` | ELF ARM64 aarch64 | Statically linked |
| `lib/wine/aarch64-unix/*.so` | ELF ARM64 aarch64 | Android shared objects |
| `lib/wine/aarch64-windows/*.dll` | PE32+ ARM64 | Windows ARM64 DLLs |
| `lib/wine/i386-windows/*.dll` | PE32 x86 | 32-bit Windows DLLs for WoW64 |

The ARM64 NDK target is **Android 28** (Android 9.0+).

## profile.json Format

```json
{
  "type": "Proton",
  "versionName": "10-arm64ec",
  "versionCode": 0,
  "description": "Proton 10 arm64ec for newer cmod versions",
  "files": [],
  "proton": {
    "binPath": "bin",
    "libPath": "lib",
    "prefixPack": "prefixPack.txz"
  }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Must be `"Proton"` (NOT `"Wine"`) for Proton packages |
| `versionName` | string | Human-readable version identifier shown in Winlator UI |
| `versionCode` | integer | Numeric version for update comparison; 0 is acceptable |
| `description` | string | Description shown in Winlator UI |
| `files` | array | Additional file mappings; empty `[]` in reference build |
| `proton.binPath` | string | Path to native binary directory relative to archive root |
| `proton.libPath` | string | Path to Wine library directory relative to archive root |
| `proton.prefixPack` | string | Filename of the default prefix XZ archive |

**Key finding:** The `type` field is `"Proton"`, NOT `"Wine"`. This is what Winlator uses to distinguish Proton packages from plain Wine packages.

## Size Summary

| Component | Size |
|-----------|------|
| Compressed .wcp | 222 MB |
| Total uncompressed | 1,436 MB |
| bin/ | 3.6 MB |
| lib/ | 1,400 MB |
| share/ | 12 MB |
| prefixPack.txz | 23 MB |
| profile.json | <1 KB |

## aarch64-unix Libraries (32 files)

These are the native Unix-side Wine modules that interface with Android:
```
amd_ags_x64.so   avicap32.so    bcrypt.so      crypt32.so
ctapi32.so       dnsapi.so      dwrite.so      kerberos.so
localspl.so      mountmgr.so    msv1_0.so      netapi32.so
nsiproxy.so      ntdll.so       odbc32.so      opencl.so
opengl32.so      qcap.so        secur32.so     win32u.so
windows.media.speech.so         winealsa.so    winebth.so
winebus.so       winedmo.so     winegstreamer.so
wineps.so        winepulse.so   winevulkan.so
winex11.so       winspool.so    ws2_32.so
```

## Packaging (Creating a .wcp)

```bash
# Inside the directory containing bin/, lib/, share/, profile.json, prefixPack.txz:
tar -cf - . | zstd -T0 -19 -o output.wcp

# Or with Python:
python3 -c "
import zstandard, tarfile, os
cctx = zstandard.ZstdCompressor(level=19, threads=-1)
with open('output.wcp', 'wb') as out:
    with cctx.stream_writer(out) as writer:
        with tarfile.open(fileobj=writer, mode='w|') as tf:
            tf.add('.', recursive=True)
"
```
