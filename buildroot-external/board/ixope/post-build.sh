#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# IXOPE post-build — Fast boot optimizations
# Strategy: Keep Buildroot's default rcS, but remove slow scripts
# and ensure our overlay scripts (S50xorg, S99ixope) run fast.
# ═══════════════════════════════════════════════════════════════════════

TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"

echo "=== IXOPE Post-Build ==="

# ─── Remove slow/unnecessary default init scripts ──────────────────────
# These add seconds of delay and aren't needed for our kiosk app
rm -f "$TARGET_DIR/etc/init.d/S01logging" 2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S20urandom" 2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S40network" 2>/dev/null

# ─── Add fast-boot scripts ─────────────────────────────────────────────
# S00dmesg — suppress kernel console spam (instant)
cat > "$TARGET_DIR/etc/init.d/S00dmesg" << 'EOF'
#!/bin/sh
case "$1" in start) dmesg -n 1 ;; esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S00dmesg"

# S01cpufreq — performance governor (instant)
cat > "$TARGET_DIR/etc/init.d/S01cpufreq" << 'EOF'
#!/bin/sh
case "$1" in
  start)
    for g in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
      [ -f "$g" ] && echo performance > "$g" 2>/dev/null
    done
    ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S01cpufreq"

# S10modules — load WiFi driver (no sleep, no polling)
cat > "$TARGET_DIR/etc/init.d/S10modules" << 'EOF'
#!/bin/sh
case "$1" in
  start)
    if [ -d /lib/modules ]; then
      KVER=$(ls /lib/modules/ | head -1)
      [ -n "$KVER" ] && depmod -a "$KVER" 2>/dev/null
      modprobe aic8800_bsp 2>/dev/null
      modprobe aic8800_fdrv 2>/dev/null
    fi
    ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S10modules"

# ─── extlinux.conf — kernel boot config ───────────────────────────────
mkdir -p "$TARGET_DIR/boot/extlinux"
cat > "$TARGET_DIR/boot/extlinux/extlinux.conf" << 'EOF'
default ixope
timeout 0

label ixope
    kernel /boot/Image
    fdt /boot/rk3566-radxa-zero-3w-ap6212.dtb
    append root=/dev/mmcblk1p1 rootfstype=ext4 rootwait rw quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 console=ttyS2,1500000
EOF

# ─── fstab — fast mount options ────────────────────────────────────────
cat > "$TARGET_DIR/etc/fstab" << 'EOF'
/dev/root       /                ext4    rw,noatime,nodiratime   0      1
sysfs           /sys             sysfs   defaults                0      0
proc            /proc            proc    defaults                0      0
tmpfs           /tmp             tmpfs   defaults,nosuid,size=64M 0     0
tmpfs           /var/run         tmpfs   defaults,nosuid,size=8M  0     0
/dev/mmcblk1p2  /var/ixope-data  ext4    rw,noatime,nosuid       0      2
EOF

# ─── Hostname ──────────────────────────────────────────────────────────
echo "ixope" > "$TARGET_DIR/etc/hostname"

# ─── NetworkManager non-blocking ───────────────────────────────────────
mkdir -p "$TARGET_DIR/etc/NetworkManager/conf.d"
cat > "$TARGET_DIR/etc/NetworkManager/conf.d/wifi.conf" << 'EOF'
[device]
wifi.scan-rand-mac-address=no

[main]
no-auto-default=*
EOF

# ─── WiFi firmware symlink ─────────────────────────────────────────────
mkdir -p "$TARGET_DIR/vendor/etc"
ln -sf /lib/firmware/aic8800D80 "$TARGET_DIR/vendor/etc/firmware"

# ─── U-Boot splash logo ────────────────────────────────────────────────
# Copy deploy/logo.bmp to /boot/splash.bmp so U-Boot can load it
IXOPE_ROOT="$(cd "$BOARD_DIR/../../../" && pwd)"
LOGO_SRC="$IXOPE_ROOT/deploy/logo.bmp"
if [ -f "$LOGO_SRC" ]; then
    cp "$LOGO_SRC" "$TARGET_DIR/boot/splash.bmp"
    echo "[OK] Splash logo copied from deploy/logo.bmp to /boot/splash.bmp"
else
    echo "[FAIL] deploy/logo.bmp not found at $LOGO_SRC"
    echo "       Place your 480x480 BMP logo at: deploy/logo.bmp"
    exit 1
fi

# ─── boot.scr fallback ────────────────────────────────────────────────
if command -v mkimage >/dev/null 2>&1; then
    mkimage -C none -A arm64 -T script -d "$BOARD_DIR/boot.cmd" \
        "$TARGET_DIR/boot/boot.scr" >/dev/null 2>&1
fi

# ─── Data directories ─────────────────────────────────────────────────
mkdir -p "$TARGET_DIR/var/ixope-data"
mkdir -p "$TARGET_DIR/etc/dropbear"

# ─── Ensure all init scripts are executable ────────────────────────────
chmod +x "$TARGET_DIR"/etc/init.d/S* 2>/dev/null

echo "=== IXOPE Post-Build DONE ==="
