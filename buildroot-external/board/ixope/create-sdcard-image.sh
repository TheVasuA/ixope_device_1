#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# IXOPE — Create a ready-to-flash SD card / eMMC image
# Official Radxa Zero 3W BSP kernel 5.10
# ═══════════════════════════════════════════════════════════════════════════════
#
# USAGE:
#   After building with Buildroot:
#     cd ~/buildroot
#     bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh ~/buildroot/output/images
#
# OUTPUT:
#   output/images/ixope-sdcard.img      (raw image, ~800MB)
#   output/images/ixope-sdcard.img.gz   (compressed, ~100-150MB)
#
# FLASH:
#   Linux:   gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/sdX bs=4M status=progress
#   Windows: Use Balena Etcher (accepts .img.gz directly)
#   Mac:     gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/diskN bs=4m
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Paths (works both standalone and as Buildroot POST_IMAGE_SCRIPT)
if [ -n "$1" ] && [ -d "$1" ]; then
    BUILDROOT_OUTPUT="$1"
else
    BUILDROOT_OUTPUT="${BUILDROOT_OUTPUT:-$(pwd)/output/images}"
fi

# Find the board directory (for pre-built u-boot)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOTFS="$BUILDROOT_OUTPUT/rootfs.ext4"
OUTPUT_IMG="$BUILDROOT_OUTPUT/ixope-sdcard.img"

# Find U-Boot: first check buildroot output, then board dir (pre-built fallback)
if [ -f "$BUILDROOT_OUTPUT/u-boot-rockchip.bin" ]; then
    UBOOT="$BUILDROOT_OUTPUT/u-boot-rockchip.bin"
elif [ -f "$SCRIPT_DIR/u-boot-rockchip.bin" ]; then
    UBOOT="$SCRIPT_DIR/u-boot-rockchip.bin"
else
    echo "ERROR: Missing u-boot-rockchip.bin"
    echo "Build U-Boot: make -j4 (enabled in defconfig)"
    echo "Or download pre-built: bash $SCRIPT_DIR/download-blobs.sh"
    exit 1
fi

if [ ! -f "$ROOTFS" ]; then
    echo "ERROR: Missing $ROOTFS"
    echo "Did you run 'make -j4' first?"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo " Creating IXOPE SD card image (Official Radxa Zero 3W BSP)"
echo "═══════════════════════════════════════════════════════════════"

# ─── Image layout ─────────────────────────────────────────────────────
# Offset        | Content
# 0 - 32KB      | GPT header
# 32KB - 16MB   | U-Boot (raw, at sector 64 = 32KB)
# 16MB - 528MB  | Partition 1: rootfs (ext4, 512MB)
# 528MB - 800MB | Partition 2: data (ext4, ~270MB, formatted empty)
# ──────────────────────────────────────────────────────────────────────

IMG_SIZE_MB=800
ROOTFS_START_MB=16
ROOTFS_END_MB=528
DATA_START_MB=528

echo "[1/6] Creating empty ${IMG_SIZE_MB}MiB image..."
dd if=/dev/zero of="$OUTPUT_IMG" bs=1M count=$IMG_SIZE_MB status=none

echo "[2/6] Writing partition table (GPT)..."
parted -s "$OUTPUT_IMG" mklabel gpt
parted -s "$OUTPUT_IMG" mkpart rootfs ext4 ${ROOTFS_START_MB}MiB ${ROOTFS_END_MB}MiB
parted -s "$OUTPUT_IMG" mkpart data ext4 ${DATA_START_MB}MiB 100%

echo "[3/6] Writing U-Boot bootloader (at 32KB offset)..."
dd if="$UBOOT" of="$OUTPUT_IMG" seek=64 bs=512 conv=notrunc status=none

echo "[4/6] Writing rootfs (ext4)..."
dd if="$ROOTFS" of="$OUTPUT_IMG" bs=1M seek=$ROOTFS_START_MB conv=notrunc status=none

echo "[5/6] Creating empty data partition (ixope-data)..."
DATA_SIZE_MB=$((IMG_SIZE_MB - DATA_START_MB - 2))
dd if=/dev/zero of=/tmp/ixope-data.ext4 bs=1M count=$DATA_SIZE_MB status=none
mkfs.ext4 -q -L "ixope-data" /tmp/ixope-data.ext4
dd if=/tmp/ixope-data.ext4 of="$OUTPUT_IMG" bs=1M seek=$DATA_START_MB conv=notrunc status=none
rm -f /tmp/ixope-data.ext4

echo "[6/6] Compressing image..."
gzip -f -k "$OUTPUT_IMG"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " DONE!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo " Image:      $OUTPUT_IMG ($(du -h "$OUTPUT_IMG" | cut -f1))"
echo " Compressed: ${OUTPUT_IMG}.gz ($(du -h "${OUTPUT_IMG}.gz" | cut -f1))"
echo ""
echo " To flash:"
echo "   Linux:   gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/sdX bs=4M"
echo "   Windows: Use Balena Etcher (drag the .img.gz file in)"
echo "   Mac:     gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/diskN bs=4m"
echo ""
echo " Put the SD card in the Radxa Zero 3W → power on → app in ~5s."
echo "═══════════════════════════════════════════════════════════════"
