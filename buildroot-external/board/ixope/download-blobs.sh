#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# Download Rockchip boot blobs for RK3566 (Radxa Zero 3W)
# These are required to build U-Boot from source:
#   - DDR init binary (ROCKCHIP_TPL)
#   - ARM Trusted Firmware BL31 (BL31)
#
# Run ONCE before building:
#   bash ~/ixope/buildroot-external/board/ixope/download-blobs.sh
# ═══════════════════════════════════════════════════════════════════════

BOARD_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "═══ Downloading RK3566 boot blobs ═══"

# Clone rkbin if not already present
RKBIN_DIR="$BOARD_DIR/rkbin"
if [ ! -d "$RKBIN_DIR" ]; then
    echo "Cloning Rockchip rkbin repository (shallow)..."
    git clone --depth 1 https://github.com/rockchip-linux/rkbin.git "$RKBIN_DIR"
else
    echo "rkbin already cloned, updating..."
    cd "$RKBIN_DIR" && git pull && cd "$BOARD_DIR"
fi

# Copy DDR init binary for RK3566
DDR_BIN=$(find "$RKBIN_DIR/bin/rk35" -name "rk3566_ddr_1056MHz_v*.bin" | sort -V | tail -1)
if [ -n "$DDR_BIN" ]; then
    cp "$DDR_BIN" "$BOARD_DIR/ddr.bin"
    echo "[OK] DDR binary: $(basename $DDR_BIN)"
else
    echo "[FAIL] Could not find RK3566 DDR binary in rkbin"
    exit 1
fi

# Copy BL31 (ARM Trusted Firmware) for RK3568 (same family as RK3566)
BL31_ELF=$(find "$RKBIN_DIR/bin/rk35" -name "rk3568_bl31_v*.elf" | sort -V | tail -1)
if [ -n "$BL31_ELF" ]; then
    cp "$BL31_ELF" "$BOARD_DIR/bl31.elf"
    echo "[OK] BL31 binary: $(basename $BL31_ELF)"
else
    echo "[FAIL] Could not find RK3568 BL31 ELF in rkbin"
    exit 1
fi

# Clean up rkbin (large repo, not needed after extracting blobs)
rm -rf "$RKBIN_DIR"

echo ""
echo "═══ DONE ═══"
echo "DDR:  $BOARD_DIR/ddr.bin"
echo "BL31: $BOARD_DIR/bl31.elf"
echo ""
echo "Now run: cd ~/buildroot && make -j4"
