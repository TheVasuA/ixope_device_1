#!/bin/bash
# IXOPE post-build script — runs after rootfs is assembled
# Optimizes boot for 2-5 second total boot with logo on screen at ~0.5s.

TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"

# ─── Install U-Boot splash BMP ─────────────────────────────────────────
# U-Boot displays this at power-on (before kernel loads). Never a blank screen.
if [ -f "$BOARD_DIR/splash.bmp" ]; then
    mkdir -p "$TARGET_DIR/boot"
    cp "$BOARD_DIR/splash.bmp" "$TARGET_DIR/boot/splash.bmp"
    echo "Installed U-Boot splash logo."
fi

# ─── Kernel command line for fast boot ─────────────────────────────────
# Applied via extlinux.conf or U-Boot environment
mkdir -p "$TARGET_DIR/boot/extlinux"
cat > "$TARGET_DIR/boot/extlinux/extlinux.conf" << 'EOF'
default ixope
timeout 0

label ixope
    kernel /boot/Image
    fdt /boot/rk3566-radxa-zero-3w.dtb
    append root=/dev/mmcblk1p1 rootfstype=ext4 rootwait rw quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 console=ttyS2,1500000
EOF

# ─── Remove unnecessary init scripts that slow boot ─────────────────────
rm -f "$TARGET_DIR/etc/init.d/S01logging"  2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S20urandom"  2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S40network"  2>/dev/null

# ─── Create optimized rcS to run init scripts in parallel ───────────────
cat > "$TARGET_DIR/etc/init.d/rcS" << 'EOFRC'
#!/bin/sh
# Fast parallel init — only essential scripts
for i in /etc/init.d/S??*; do
    [ ! -x "$i" ] && continue
    case "$i" in
        *.sh) . "$i" start ;;
        *)    "$i" start &  ;;
    esac
done
wait
EOFRC
chmod 755 "$TARGET_DIR/etc/init.d/rcS"

# ─── Create fstab — read-only rootfs + tmpfs + data partition ────────────
cat > "$TARGET_DIR/etc/fstab" << 'EOF'
# <device>      <mount>          <type>  <options>               <dump> <fsck>
/dev/root       /                ext4    rw,noatime,nodiratime   0      1
sysfs           /sys             sysfs   defaults                0      0
proc            /proc            proc    defaults                0      0
tmpfs           /tmp             tmpfs   defaults,nosuid,size=64M 0     0
tmpfs           /var/run         tmpfs   defaults,nosuid,size=8M  0     0
/dev/mmcblk1p2  /var/ixope-data  ext4    rw,noatime,nosuid       0      2
EOF

# ─── Set hostname ──────────────────────────────────────────────────────
echo "ixope" > "$TARGET_DIR/etc/hostname"

# ─── Network manager auto-start WiFi (non-blocking) ───────────────────
mkdir -p "$TARGET_DIR/etc/NetworkManager/conf.d"
cat > "$TARGET_DIR/etc/NetworkManager/conf.d/wifi.conf" << 'EOF'
[device]
wifi.scan-rand-mac-address=no

[main]
# Don't block boot waiting for network
no-auto-default=*
EOF

# ─── CPU governor: performance at boot ─────────────────────────────────
cat > "$TARGET_DIR/etc/init.d/S01cpufreq" << 'EOF'
#!/bin/sh
case "$1" in
  start)
    for gov in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
      [ -f "$gov" ] && echo performance > "$gov" 2>/dev/null
    done
    ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S01cpufreq"

# ─── Disable kernel console output (even faster) ──────────────────────
cat > "$TARGET_DIR/etc/init.d/S00dmesg" << 'EOF'
#!/bin/sh
case "$1" in
  start) dmesg -n 1 ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S00dmesg"

# ─── Generate U-Boot boot script (boot.scr) ───────────────────────────
if command -v mkimage >/dev/null 2>&1; then
    mkimage -C none -A arm64 -T script -d "$BOARD_DIR/boot.cmd" \
        "$TARGET_DIR/boot/boot.scr" >/dev/null 2>&1
    echo "Generated boot.scr with splash support."
fi

# ─── Install DSI panel device tree overlay ─────────────────────────────
if [ -f "$BOARD_DIR/ixope-dsi-panel.dts" ]; then
    mkdir -p "$TARGET_DIR/boot/overlays"
    cp "$BOARD_DIR/ixope-dsi-panel.dts" "$TARGET_DIR/boot/overlays/"
    echo "Installed DSI panel overlay source."
fi

echo "Post-build complete. Target boot: 2-5 seconds with logo."

# ─── WiFi firmware NVRAM file for Radxa Zero 3W (AP6212/BCM43430) ──────
# The brcmfmac driver looks for a board-specific NVRAM .txt file.
# Create symlinks so it finds the AP6212 config for this board.
mkdir -p "$TARGET_DIR/lib/firmware/brcm"
if [ -f "$TARGET_DIR/lib/firmware/brcm/brcmfmac43430-sdio.AP6212.txt" ]; then
    ln -sf brcmfmac43430-sdio.AP6212.txt \
        "$TARGET_DIR/lib/firmware/brcm/brcmfmac43430-sdio.radxa,zero-3w.txt"
    echo "WiFi: linked AP6212 NVRAM for Radxa Zero 3W."
fi

# ─── Ensure all init scripts are executable ────────────────────────────
chmod +x "$TARGET_DIR"/etc/init.d/S* 2>/dev/null
