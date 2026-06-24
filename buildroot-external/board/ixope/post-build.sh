#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# IXOPE post-build script — Official Radxa Zero 3W BSP kernel 5.10
# Optimizes boot for 2-5 second total boot with logo on screen at ~0.5s.
# ═══════════════════════════════════════════════════════════════════════

TARGET_DIR="$1"
BOARD_DIR="$(dirname "$0")"

echo "═══ IXOPE Post-Build: Applying fast-boot optimizations ═══"

# ─── Install U-Boot splash BMP ─────────────────────────────────────────
if [ -f "$BOARD_DIR/splash.bmp" ]; then
    mkdir -p "$TARGET_DIR/boot"
    cp "$BOARD_DIR/splash.bmp" "$TARGET_DIR/boot/splash.bmp"
    echo "[OK] Installed U-Boot splash logo."
fi

# ─── extlinux.conf — primary boot configuration ───────────────────────
mkdir -p "$TARGET_DIR/boot/extlinux"
cat > "$TARGET_DIR/boot/extlinux/extlinux.conf" << 'EOF'
default ixope
timeout 0

label ixope
    kernel /boot/Image
    fdt /boot/rk3566-radxa-zero-3w-ap6212.dtb
    append root=/dev/mmcblk1p1 rootfstype=ext4 rootwait rw quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 console=ttyS2,1500000
EOF
echo "[OK] Generated extlinux.conf"

# ─── Remove unnecessary init scripts that slow boot ─────────────────────
rm -f "$TARGET_DIR/etc/init.d/S01logging"  2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S20urandom"  2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S40network"  2>/dev/null
echo "[OK] Removed slow init scripts (S01logging, S20urandom, S40network)"

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
echo "[OK] Created parallel rcS init"

# ─── fstab — rootfs + tmpfs + data partition ─────────────────────────────
cat > "$TARGET_DIR/etc/fstab" << 'EOF'
# <device>      <mount>          <type>  <options>               <dump> <fsck>
/dev/root       /                ext4    rw,noatime,nodiratime   0      1
sysfs           /sys             sysfs   defaults                0      0
proc            /proc            proc    defaults                0      0
tmpfs           /tmp             tmpfs   defaults,nosuid,size=64M 0     0
tmpfs           /var/run         tmpfs   defaults,nosuid,size=8M  0     0
/dev/mmcblk1p2  /var/ixope-data  ext4    rw,noatime,nosuid       0      2
EOF
echo "[OK] Generated fstab with data partition"

# ─── Hostname ──────────────────────────────────────────────────────────
echo "ixope" > "$TARGET_DIR/etc/hostname"

# ─── NetworkManager — non-blocking WiFi at boot ────────────────────────
mkdir -p "$TARGET_DIR/etc/NetworkManager/conf.d"
cat > "$TARGET_DIR/etc/NetworkManager/conf.d/wifi.conf" << 'EOF'
[device]
wifi.scan-rand-mac-address=no

[main]
no-auto-default=*
EOF
echo "[OK] Configured NetworkManager (non-blocking)"

# ─── S00dmesg — suppress kernel console output ────────────────────────
cat > "$TARGET_DIR/etc/init.d/S00dmesg" << 'EOF'
#!/bin/sh
case "$1" in
  start) dmesg -n 1 ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S00dmesg"

# ─── S01cpufreq — performance governor at boot ────────────────────────
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
echo "[OK] Created S00dmesg + S01cpufreq init scripts"

# ─── Generate U-Boot boot script (boot.scr) — fallback ────────────────
if command -v mkimage >/dev/null 2>&1; then
    mkimage -C none -A arm64 -T script -d "$BOARD_DIR/boot.cmd" \
        "$TARGET_DIR/boot/boot.scr" >/dev/null 2>&1
    echo "[OK] Generated boot.scr (fallback)"
fi

# ─── WiFi: AIC8800 firmware path symlink ──────────────────────────────
# The AIC8800 driver hardcodes firmware path to /vendor/etc/firmware/
# (Android convention). Symlink it to the actual firmware location.
mkdir -p "$TARGET_DIR/vendor/etc"
ln -sf /lib/firmware/aic8800D80 "$TARGET_DIR/vendor/etc/firmware"
echo "[OK] WiFi: Symlinked /vendor/etc/firmware -> /lib/firmware/aic8800D80"
# The aic8800-wifi package installs .ko files and firmware.
# Ensure modules load at boot (BusyBox init doesn't use systemd modules-load).
mkdir -p "$TARGET_DIR/etc/init.d"
cat > "$TARGET_DIR/etc/init.d/S10modules" << 'EOF'
#!/bin/sh
case "$1" in
  start)
    # Load AIC8800 WiFi modules
    if [ -d /lib/modules ]; then
        KVER=$(ls /lib/modules/ | head -1)
        if [ -n "$KVER" ]; then
            depmod -a "$KVER" 2>/dev/null
            modprobe aic8800_bsp 2>/dev/null
            sleep 2
            modprobe aic8800_fdrv 2>/dev/null
        fi
    fi
    # Wait for wlan interface to appear
    for i in 1 2 3 4 5 6 7 8 9 10; do
        [ -d /sys/class/net/wlan0 ] && break
        sleep 1
    done
    ;;
esac
EOF
chmod 755 "$TARGET_DIR/etc/init.d/S10modules"
echo "[OK] WiFi: Created S10modules init script for AIC8800"

# ─── Create data directory mount point ─────────────────────────────────
mkdir -p "$TARGET_DIR/var/ixope-data"

# ─── Ensure all init scripts are executable ────────────────────────────
chmod +x "$TARGET_DIR"/etc/init.d/S* 2>/dev/null

echo "═══ IXOPE Post-Build: DONE — target boot: 2-5 seconds ═══"
