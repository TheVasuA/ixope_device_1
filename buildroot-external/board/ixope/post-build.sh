#!/bin/bash
# IXOPE post-build script — runs after rootfs is assembled
# Optimizes boot speed and sets up the data partition.

TARGET_DIR="$1"

# ─── Kernel command line for fast boot ─────────────────────────────────
# These are applied via extlinux.conf or U-Boot environment
CMDLINE="quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0"

# ─── Remove unnecessary init scripts that slow boot ─────────────────────
rm -f "$TARGET_DIR/etc/init.d/S01logging"  2>/dev/null
rm -f "$TARGET_DIR/etc/init.d/S20urandom"  2>/dev/null

# ─── Create fstab for data partition ─────────────────────────────────────
cat > "$TARGET_DIR/etc/fstab" << 'EOF'
# <device>      <mount>          <type>  <options>           <dump> <fsck>
/dev/root       /                ext4    ro,noatime          0      1
tmpfs           /tmp             tmpfs   defaults,nosuid     0      0
tmpfs           /var/run         tmpfs   defaults,nosuid     0      0
/dev/mmcblk0p3  /var/ixope-data  ext4    rw,noatime,nosuid   0      2
EOF

# ─── Set hostname ──────────────────────────────────────────────────────
echo "ixope" > "$TARGET_DIR/etc/hostname"

# ─── Network manager auto-start WiFi ──────────────────────────────────
mkdir -p "$TARGET_DIR/etc/NetworkManager/conf.d"
cat > "$TARGET_DIR/etc/NetworkManager/conf.d/wifi.conf" << 'EOF'
[device]
wifi.scan-rand-mac-address=no
EOF

echo "Post-build complete."
