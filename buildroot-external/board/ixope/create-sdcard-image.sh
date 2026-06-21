#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# IXOPE — Create a ready-to-flash SD card / eMMC image
# ═══════════════════════════════════════════════════════════════════════════════
#
# USAGE:
#   After building with Buildroot:
#     cd ~/buildroot
#     bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh
#
# OUTPUT:
#   output/images/ixope-sdcard.img      (raw image)
#   output/images/ixope-sdcard.img.gz   (compressed, send this to your friend)
#
# YOUR FRIEND:
#   On Linux:   gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/sdX bs=4M status=progress
#   On Windows: Use Balena Etcher (accepts .img.gz directly, no need to unzip)
#   On Mac:     gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/diskN bs=4m
#
# Then put the SD card in the device and power on. Done.
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Paths (works both standalone and as Buildroot POST_IMAGE_SCRIPT)
if [ -n "$1" ] && [ -d "$1" ]; then
    # Called by Buildroot: $1 = output/images directory
    BUILDROOT_OUTPUT="$1"
else
    BUILDROOT_OUTPUT="${BUILDROOT_OUTPUT:-$(pwd)/output/images}"
fi
UBOOT="$BUILDROOT_OUTPUT/u-boot-rockchip.bin"
ROOTFS="$BUILDROOT_OUTPUT/rootfs.ext4"
OUTPUT_IMG="$BUILDROOT_OUTPUT/ixope-sdcard.img"

# Sanity checks
for f in "$UBOOT" "$ROOTFS"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Missing $f"
        echo "Did you run 'make' first? (make -j\$(nproc))"
        exit 1
    fi
done

echo "═══════════════════════════════════════════════════════════════"
echo " Creating IXOPE SD card image"
echo "═══════════════════════════════════════════════════════════════"

# ─── Image layout ─────────────────────────────────────────────────────
# Offset        | Content
# 0 - 32KB      | GPT header
# 32KB - 16MB   | U-Boot (raw, at sector 64 = 32KB)
# 16MB - 272MB  | Partition 1: rootfs (ext4, 256MB)
# 272MB - 528MB | Partition 2: data (ext4, 256MB, formatted empty)
# ──────────────────────────────────────────────────────────────────────

IMG_SIZE_MB=784
ROOTFS_START_MB=16
ROOTFS_END_MB=528
DATA_START_MB=528
DATA_END_MB=$((IMG_SIZE_MB - 1))

echo "[1/6] Creating empty ${IMG_SIZE_MB}MB image..."
dd if=/dev/zero of="$OUTPUT_IMG" bs=1M count=$IMG_SIZE_MB status=none

echo "[2/6] Writing partition table (GPT)..."
parted -s "$OUTPUT_IMG" mklabel gpt
parted -s "$OUTPUT_IMG" mkpart rootfs ext4 ${ROOTFS_START_MB}MB ${ROOTFS_END_MB}MB
parted -s "$OUTPUT_IMG" mkpart data ext4 ${DATA_START_MB}MB 100%

echo "[3/6] Writing U-Boot bootloader (at 32KB offset)..."
dd if="$UBOOT" of="$OUTPUT_IMG" seek=64 bs=512 conv=notrunc status=none

echo "[4/6] Writing rootfs (ext4)..."
ROOTFS_OFFSET=$((ROOTFS_START_MB * 1024 * 1024))
dd if="$ROOTFS" of="$OUTPUT_IMG" bs=1M seek=$ROOTFS_START_MB conv=notrunc status=none

echo "[5/6] Creating empty data partition..."
# Create a small ext4 filesystem for the data partition
DATA_SIZE_MB=$((DATA_END_MB - DATA_START_MB))
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
echo " Image: $OUTPUT_IMG ($(du -h "$OUTPUT_IMG" | cut -f1))"
echo " Compressed: ${OUTPUT_IMG}.gz ($(du -h "${OUTPUT_IMG}.gz" | cut -f1))"
echo ""
echo " Send '${OUTPUT_IMG}.gz' to your friend."
echo ""
echo " To flash:"
echo "   Linux:   gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/sdX bs=4M"
echo "   Windows: Use Balena Etcher (drag the .img.gz file in)"
echo "   Mac:     gunzip ixope-sdcard.img.gz && sudo dd if=ixope-sdcard.img of=/dev/diskN bs=4m"
echo ""
echo " Put the SD card in the Radxa Zero 3W and power on."
echo "═══════════════════════════════════════════════════════════════"
