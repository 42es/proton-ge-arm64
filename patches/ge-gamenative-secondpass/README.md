# GE GameNative Second Pass

Focused non-Wayland GE staging patch pack for GameNative / Winlator ARM64 experiments.

Source:
- `C:\Users\Makin\Desktop\Proton build\proton-ge-arm64\patches\ge-wine-only-wrapper`

Intent:
- keep this separate from the first-pass generic compatibility layer
- focus on X11 input/window behavior and keyboard layout handling
- avoid winecfg-heavy or Wayland-specific staging work

## Included patches

1. `winex11-Fixed-scancodes/0002-winex11-Always-create-the-HKCU-configuration-registr.patch`
2. `winex11-Fixed-scancodes/0003-winex11-Write-supported-keyboard-layout-list-in-regi.patch`
3. `winex11-Fixed-scancodes/0005-winex11-Use-the-user-configured-keyboard-layout-if-a.patch`
4. `winex11-Fixed-scancodes/0007-winex11-Use-scancode-high-bit-to-set-KEYEVENTF_EXTEN.patch`
5. `winex11-Fixed-scancodes/0008-winex11-Support-fixed-X11-keycode-to-scancode-conver.patch`
6. `winex11-ime-check-thread-data/0001-winex11.drv-handle-missing-thread-data-in-X11DRV_get_ic.patch`
7. `winex11-Window_Style/0001-winex11-Fix-handling-of-window-attributes-for-WS_EX_.patch`
8. `loader-KeyboardLayouts/0001-loader-Add-Keyboard-Layouts-registry-enteries.patch`

## Excluded from this second pass

- all `winecfg` UI patches from `winex11-Fixed-scancodes`
- `0009-winex11-Disable-keyboard-scancode-auto-detection-by-.patch`
- `winex11.drv-Query_server_position`
- `user32-FlashWindowEx`
- `wininet-Cleanup`

## Suggested apply order

1. `loader-KeyboardLayouts/0001-loader-Add-Keyboard-Layouts-registry-enteries.patch`
2. `winex11-Fixed-scancodes/0002-winex11-Always-create-the-HKCU-configuration-registr.patch`
3. `winex11-Fixed-scancodes/0003-winex11-Write-supported-keyboard-layout-list-in-regi.patch`
4. `winex11-Fixed-scancodes/0005-winex11-Use-the-user-configured-keyboard-layout-if-a.patch`
5. `winex11-Fixed-scancodes/0007-winex11-Use-scancode-high-bit-to-set-KEYEVENTF_EXTEN.patch`
6. `winex11-Fixed-scancodes/0008-winex11-Support-fixed-X11-keycode-to-scancode-conver.patch`
7. `winex11-ime-check-thread-data/0001-winex11.drv-handle-missing-thread-data-in-X11DRV_get_ic.patch`
8. `winex11-Window_Style/0001-winex11-Fix-handling-of-window-attributes-for-WS_EX_.patch`

## Notes

- This pack is intentionally runtime-focused. It omits the `winecfg` tab/config UI work from the original GE staging family.
- `0002` is included because later X11 registry writes are less reliable if the HKCU X11 key does not exist.
- `0008` is the highest-value patch in this pack; the rest mainly support predictable scancode/layout behavior around it.
- Treat this as opt-in until the first-pass GE donor stack is stable.
