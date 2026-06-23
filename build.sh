#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# IXOPE — Complete Build Script for WSL2
# Automatically installs deps, clones repos, fixes errors, and builds image.
# ═══════════════════════════════════════════════════════════════════════════════
#
# USAGE (run inside WSL2 terminal):
#   cd /mnt/d/infiniti/medical/ixope
#   bash build.sh
#
# OUTPUT:
#   /mnt/d/ixope-sdcard.img.gz  (ready to flash with Balena Etcher)
# ═══════════════════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "${GREEN}[IXOPE]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ─── Configuration ─────────────────────────────────────────────────────
IXOPE_SRC="/mnt/d/infiniti/medical/ixope"
BUILD_HOME="$HOME/ixope-build"
BUILDROOT_DIR="$BUILD_HOME/buildroot"
IXOPE_DIR="$BUILD_HOME/ixope"
BUILDROOT_VERSION="2024.02"
OUTPUT_DEST="/mnt/d"

# ─── Step 1: Install build dependencies ───────────────────────────────
log "Step 1: Installing build dependencies..."
sudo apt update -qq
sudo apt install -y -qq \
    build-essential gcc g++ make git wget curl unzip bc \
    libncurses-dev flex bison libssl-dev libelf-dev \
    python3 python3-dev python3-setuptools \
    file cpio rsync dosfstools mtools parted \
    device-tree-compiler u-boot-tools gzip \
    libfdt-dev swig 2>/dev/null
log "Dependencies installed."

# ─── Step 2: Set up build directory (on Linux filesystem for speed) ────
log "Step 2: Setting up build directory at $BUILD_HOME..."
mkdir -p "$BUILD_HOME"

# ─── Step 3: Clone/update Buildroot ───────────────────────────────────
if [ ! -d "$BUILDROOT_DIR/.git" ]; then
    log "Cloning Buildroot $BUILDROOT_VERSION..."
    git clone --depth 1 --branch "$BUILDROOT_VERSION" \
        https://github.com/buildroot/buildroot.git "$BUILDROOT_DIR"
else
    log "Buildroot already cloned."
    cd "$BUILDROOT_DIR"
    git checkout "$BUILDROOT_VERSION" 2>/dev/null || true
fi

# ─── Step 4: Copy IXOPE source to Linux filesystem ────────────────────
log "Step 4: Syncing IXOPE source to Linux filesystem..."
mkdir -p "$IXOPE_DIR"
rsync -a --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='dev_data' \
    "$IXOPE_SRC/" "$IXOPE_DIR/"
log "Source synced."

# ─── Step 5: Fix common issues before build ───────────────────────────
log "Step 5: Pre-build fixes..."

# Fix line endings (Windows → Unix)
find "$IXOPE_DIR/buildroot-external" -type f \( -name "*.sh" -o -name "*.cmd" -o -name "*.fragment" -o -name "*.dts" -o -name "*.mk" -o -name "*.in" -o -name "defconfig" -o -name "*.desc" -o -name "*.conf" \) -exec sed -i 's/\r$//' {} \;
log "Fixed line endings (CRLF → LF)."

# Make shell scripts executable
chmod +x "$IXOPE_DIR/buildroot-external/board/ixope/"*.sh
chmod +x "$IXOPE_DIR/buildroot-external/rootfs-overlay/etc/init.d/"* 2>/dev/null || true
log "Made scripts executable."

# Verify external.desc exists
if [ ! -f "$IXOPE_DIR/buildroot-external/external.desc" ]; then
    error "Missing external.desc! Creating..."
    echo -e "name: IXOPE\ndesc: IXOPE Medical Device - Buildroot External Tree" \
        > "$IXOPE_DIR/buildroot-external/external.desc"
fi

# ─── Step 5b: Fix PATH (Buildroot requires no spaces/tabs/newlines) ────
log "Step 5b: Sanitizing PATH..."
# Remove any PATH entries with spaces (common on WSL with Windows paths)
CLEAN_PATH=""
IFS=':' read -ra PATHPARTS <<< "$PATH"
for p in "${PATHPARTS[@]}"; do
    # Skip entries with spaces, tabs, or that point to /mnt/c/... Windows paths
    if [[ "$p" == *" "* ]] || [[ "$p" == *$'\t'* ]] || [[ "$p" == /mnt/c/* ]] || [[ "$p" == /mnt/d/* ]]; then
        continue
    fi
    if [ -n "$CLEAN_PATH" ]; then
        CLEAN_PATH="$CLEAN_PATH:$p"
    else
        CLEAN_PATH="$p"
    fi
done
export PATH="$CLEAN_PATH"
log "PATH cleaned. Entries with spaces/Windows paths removed."
echo "  PATH=$PATH"

# ─── Step 6: Configure Buildroot ──────────────────────────────────────
log "Step 6: Configuring Buildroot with IXOPE defconfig..."
cd "$BUILDROOT_DIR"
export BR2_EXTERNAL="$IXOPE_DIR/buildroot-external"

# Clean old config if switching
if [ -f ".config" ]; then
    # Check if BR2_EXTERNAL changed
    if ! grep -q "BR2_EXTERNAL_IXOPE_PATH" .config 2>/dev/null; then
        warn "Old config detected. Cleaning..."
        make clean 2>/dev/null || true
    fi
fi

make ixope_rk3566_defconfig
log "Configuration loaded."

# ─── Step 7: Build ────────────────────────────────────────────────────
log "Step 7: Building image (this takes 45-90 min first time)..."
log "Using $(nproc) CPU cores (limited to 4 for stability)..."

BUILD_CORES=4
MAX_RETRIES=3
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    set +e
    make -j${BUILD_CORES} 2>&1 | tee "$BUILD_HOME/build.log"
    BUILD_EXIT=${PIPESTATUS[0]}
    set -e

    if [ $BUILD_EXIT -eq 0 ]; then
        log "Build SUCCESS!"
        break
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -ge $MAX_RETRIES ]; then
            error "Build failed after $MAX_RETRIES attempts."
            error "Check log: $BUILD_HOME/build.log"
            tail -50 "$BUILD_HOME/build.log"
            exit 1
        fi

        warn "Build failed (attempt $RETRY/$MAX_RETRIES). Analyzing error..."

        # Common error: PATH has spaces (WSL Windows paths leak in)
        if grep -q "PATH contains spaces" "$BUILD_HOME/build.log"; then
            warn "PATH still has spaces. Stripping ALL Windows paths..."
            export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            continue
        fi

        # Common error: package download failure → retry
        if grep -q "ERROR.*download" "$BUILD_HOME/build.log"; then
            warn "Download error detected. Retrying..."
            sleep 5
            continue
        fi

        # Common error: missing host tool
        if grep -q "command not found" "$BUILD_HOME/build.log"; then
            MISSING=$(grep "command not found" "$BUILD_HOME/build.log" | head -1 | awk '{print $NF}')
            warn "Missing tool: $MISSING — attempting install..."
            sudo apt install -y "$MISSING" 2>/dev/null || true
            continue
        fi

        # Common error: disk space
        if grep -q "No space left" "$BUILD_HOME/build.log"; then
            error "Disk full! Need at least 15GB free. Exiting."
            exit 1
        fi

        # Common error: U-Boot defconfig not found
        if grep -q "radxa-zero-3-rk3566_defconfig.*not found\|No rule to make.*defconfig" "$BUILD_HOME/build.log"; then
            warn "U-Boot defconfig issue. Falling back to evb-rk3568..."
            sed -i 's/BR2_TARGET_UBOOT_BOARD_DEFCONFIG=.*/BR2_TARGET_UBOOT_BOARD_DEFCONFIG="evb-rk3568"/' \
                "$IXOPE_DIR/buildroot-external/configs/ixope_rk3566_defconfig"
            make ixope_rk3566_defconfig
            continue
        fi

        # Common error: kernel config option doesn't exist
        if grep -q "CONFIG_.*not in final" "$BUILD_HOME/build.log"; then
            warn "Kernel config warning (non-fatal). Retrying..."
            continue
        fi

        # Generic: retry with single core (often fixes race conditions)
        warn "Unknown error. Retrying with single core..."
        BUILD_CORES=1
    fi
done

# ─── Step 8: Create SD card image ─────────────────────────────────────
log "Step 8: Creating flashable SD card image..."
cd "$BUILDROOT_DIR"

if [ ! -f "output/images/u-boot-rockchip.bin" ]; then
    error "Missing u-boot-rockchip.bin in output. Build may have partially failed."
    exit 1
fi

if [ ! -f "output/images/rootfs.ext4" ]; then
    error "Missing rootfs.ext4 in output. Build may have partially failed."
    exit 1
fi

bash "$IXOPE_DIR/buildroot-external/board/ixope/create-sdcard-image.sh" \
    "$BUILDROOT_DIR/output/images"

# ─── Step 9: Copy to Windows ──────────────────────────────────────────
log "Step 9: Copying image to $OUTPUT_DEST..."
cp "$BUILDROOT_DIR/output/images/ixope-sdcard.img.gz" "$OUTPUT_DEST/"
log "Image copied to: $OUTPUT_DEST/ixope-sdcard.img.gz"

# ─── Done ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e " ${GREEN}BUILD COMPLETE!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo " Image:  $OUTPUT_DEST/ixope-sdcard.img.gz"
echo " Size:   $(du -h "$OUTPUT_DEST/ixope-sdcard.img.gz" | cut -f1)"
echo ""
echo " Flash with Balena Etcher → insert SD → power on → app in ~5s"
echo ""
echo "═══════════════════════════════════════════════════════════════"
