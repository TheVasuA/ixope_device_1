#!/bin/bash
# Download Rockchip binary blobs needed for U-Boot on RK3566
# Run this ONCE before building:
#   bash ~/ixope/buildroot-external/board/ixope/download-blobs.sh

BOARD_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Downloading Rockchip RK3566 boot blobs..."

# DDR init blob (TPL - from Rockchip rkbin)
if [ ! -f "$BOARD_DIR/rk3566_ddr_1056MHz_v1.18.bin" ]; then
    wget -q -O "$BOARD_DIR/rk3566_ddr_1056MHz_v1.18.bin" \
        "https://github.com/rockchip-linux/rkbin/raw/master/bin/rk35/rk3566_ddr_1056MHz_v1.18.bin"
    echo "[OK] Downloaded DDR init blob"
else
    echo "[OK] DDR init blob already exists"
fi

# ARM Trusted Firmware (BL31 - from Rockchip rkbin)
if [ ! -f "$BOARD_DIR/bl31.elf" ]; then
    wget -q -O "$BOARD_DIR/rk3568_bl31_v1.43.elf" \
        "https://github.com/rockchip-linux/rkbin/raw/master/bin/rk35/rk3568_bl31_v1.43.elf"
    ln -sf rk3568_bl31_v1.43.elf "$BOARD_DIR/bl31.elf"
    echo "[OK] Downloaded BL31 (ARM Trusted Firmware)"
else
    echo "[OK] BL31 already exists"
fi

echo "Done. You can now build: make -j4"
