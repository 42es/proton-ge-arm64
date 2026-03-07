# GE Wine Patch Extraction

This repo now includes a helper to extract the Wine-only patch delta from a `proton-ge-custom` checkout.

## Goal

Use this when you want the real GE Wine patch stack without dragging in the rest of the Proton wrapper repo.

It compares the GE `wine` tree against its upstream Wine base and emits:

- `patches/ge-wine-only/patches/*.patch`
- `patches/ge-wine-only/inventory.json`
- `patches/ge-wine-only/README.md`

## Usage

From the GE build repo root:

```bash
python3 scripts/extract_ge_wine_patches.py \
  --ge-root /path/to/proton-ge-custom \
  --output-dir patches/ge-wine-only \
  --fetch
```

## Notes

- `--ge-root` should point at a real `proton-ge-custom` checkout with submodules initialized.
- The script auto-detects whether the Wine tree is at:
  - `wine/`
  - `proton-wine/`
  - repo root
- The script computes the merge-base against the Wine repo's upstream remote HEAD and formats only commits on the GE side.
- This gives you the raw GE-only Wine delta. It does not decide which patches are Android-safe or GameNative-safe.

## Next step after extraction

Review `patches/ge-wine-only/README.md` and classify patches into:

- required for GameNative
- useful but optional
- desktop-only, reject

That filtered stack is what should eventually get layered after the Android/ARM64 patch chain.
