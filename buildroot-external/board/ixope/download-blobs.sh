#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Download pre-built U-Boot + Rockchip boot blobs for Radxa Zero 3W
# Run this ONCE before building:
#   bash ~/ixope/buildroot-external/board/ixope/download-blobs.sh
# ═══════════════════════════════════════════════════════════════════════

BOARD_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "═══ Downloading Radxa Zero 3W boot blobs ═══"

# Download the Radxa loader (SPL + U-Boot combined binary)
# This is the official pre-built bootloader for the Radxa Zero 3W
if [ ! -f "$BOARD_DIR/u-boot-rockchip.bin" ]; then
    echo "Downloading pre-built U-Boot for Radxa Zero 3W..."

    # Option 1: From Radxa's official loader repo
    wget -q -O "$BOARD_DIR/rk356x_spl_loader.bin" \
        "https://dl.radxa.com/rock3/images/loader/rk356x_spl_loader_ddr1056_v1.12.109.bin" && \
    cp "$BOARD_DIR/rk356x_spl_loader.bin" "$BOARD_DIR/u-boot-rockchip.bin" && \
    echo "[OK] Downloaded U-Boot/SPL loader" || \
    echo "[FAIL] Could not download loader"
else
    echo "[OK] u-boot-rockchip.bin already exists"
fi

# Verify
if [ -f "$BOARD_DIR/u-boot-rockchip.bin" ]; then
    echo ""
    echo "═══ DONE ═══"
    echo "Boot binary: $BOARD_DIR/u-boot-rockchip.bin"
    echo "Size: $(du -h "$BOARD_DIR/u-boot-rockchip.bin" | cut -f1)"
    echo ""
    echo "You can now build: cd ~/buildroot && make -j4"
else
    echo ""
    echo "═══ FAILED ═══"
    echo "Could not download boot binary. Check your internet connection."
    exit 1
fi
