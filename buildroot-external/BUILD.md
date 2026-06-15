# IXOPE Buildroot Image — Build & Install Guide

## Overview

This builds a minimal Linux image for the Radxa Zero 3W that boots directly
to the IXOPE medical camera application in ~5 seconds (eMMC) / ~7 seconds (SD).

**What's included:** Linux kernel + Python 3 + OpenCV + Pillow + Flask + Tkinter +
X11 (minimal) + WiFi (NetworkManager) + I2C tools + your IXOPE app. Nothing else.

**What's NOT included:** No desktop, no systemd, no apt, no snap, no bloat.

---

## Requirements (build machine)

- **Linux** (Ubuntu 22.04+ or similar) — NOT Windows. Use WSL2 if needed.
- ~15 GB free disk space
- ~4 GB RAM minimum
- Internet connection (downloads toolchain + packages on first build)

```bash
# Install build dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y \
    build-essential gcc g++ make \
    git wget curl unzip bc \
    libncurses-dev flex bison \
    libssl-dev libelf-dev \
    python3 python3-dev \
    file cpio rsync
```

---

## Step 1: Clone Buildroot

```bash
cd ~
git clone https://github.com/buildroot/buildroot.git
cd buildroot
git checkout 2024.02   # stable release
```

---

## Step 2: Point to the IXOPE external tree

```bash
# Assuming your ixope repo is at ~/ixope
export BR2_EXTERNAL=~/ixope/buildroot-external
```

---

## Step 3: Load the IXOPE defconfig

```bash
make ixope_rk3566_defconfig
```

This configures Buildroot with:
- RK3566 (Radxa Zero 3W) target
- Minimal rootfs (~100MB)
- Python 3 + all your dependencies
- Your IXOPE app installed at `/opt/ixope`
- BusyBox init (no systemd) for fast boot
- X11 minimal (for Tkinter)
- WiFi (NetworkManager + wpa_supplicant)

---

## Step 4: (Optional) Customize

```bash
make menuconfig        # general settings
make linux-menuconfig  # kernel config (add/remove drivers)
```

**Important kernel options to verify:**
- `CONFIG_VIDEO_V4L2=y` (camera)
- `CONFIG_I2C_RK3X=y` (I2C for your Arduino LED controller)
- `CONFIG_SERIAL_8250=y` (UART)
- `CONFIG_DRM_ROCKCHIP=y` (display)
- `CONFIG_BRCMFMAC=y` (WiFi built-in, not module)

---

## Step 5: Build

```bash
make -j$(nproc)
```

**First build: ~45-90 minutes** (downloads + compiles everything)
**Subsequent builds: ~5-10 minutes** (only rebuilds changed parts)

Output files:
```
output/images/
├── rootfs.ext4          # Root filesystem
├── Image                # Linux kernel
├── rk3566-radxa-zero-3w.dtb  # Device tree
└── u-boot-rockchip.bin  # Bootloader
```

---

## Step 6: Create the SD card / eMMC image

```bash
# Buildroot may generate sdcard.img automatically. If not:
cd output/images

# Create a partitioned image:
#   Partition 1: U-Boot (raw, offset 64 sectors)
#   Partition 2: rootfs (ext4, ~256MB)
#   Partition 3: data (ext4, remaining space — for captured images/videos)

# Simple approach — use genimage (Buildroot can do this automatically)
# Or manually:
dd if=/dev/zero of=ixope-image.img bs=1M count=512
# Write U-Boot at sector 64:
dd if=u-boot-rockchip.bin of=ixope-image.img seek=64 conv=notrunc
# Create partitions with fdisk/sfdisk, then write rootfs.ext4 to partition 2
```

For a cleaner approach, add this to the defconfig:
```
BR2_ROOTFS_POST_IMAGE_SCRIPT="$(BR2_EXTERNAL_IXOPE_PATH)/board/ixope/post-image.sh"
```

---

## Step 7: Flash to the device

### Option A: Flash to SD card

```bash
# Find your SD card device (e.g., /dev/sdb)
lsblk

# Flash the image
sudo dd if=output/images/ixope-image.img of=/dev/sdX bs=4M status=progress
sync
```

Insert the SD card into the Radxa Zero 3W and power on.

### Option B: Flash to eMMC (recommended for fast boot)

1. Put the Radxa in **Maskrom mode** (hold the boot button while powering on)
2. Use `rkdeveloptool` to flash:

```bash
# Install rkdeveloptool
sudo apt install rkdeveloptool

# Flash U-Boot
rkdeveloptool db rk3566_ddr_1056MHz_v1.18.bin
rkdeveloptool wl 64 u-boot-rockchip.bin

# Flash rootfs
rkdeveloptool wl 32768 rootfs.ext4

# Reboot
rkdeveloptool rd
```

Or use **Radxa's rkdevtool** (GUI) on Windows to flash the image.

---

## Step 8: First boot

Power on. You should see:

```
0.0s  Power LED on
0.5s  U-Boot logo (if configured)
2.0s  Kernel booting (quiet, no console text)
4.0s  X server starts
5.0s  IXOPE splash visible, camera starting
```

---

## Post-install: WiFi setup

SSH is available via `dropbear` (no password for root by default).
Connect via USB serial or Ethernet first, then:

```bash
# Connect to WiFi
nmcli dev wifi connect "YourSSID" password "YourPassword"

# Or use the app's built-in WiFi settings (tap the WiFi icon)
```

---

## Updating the app (without reflashing)

The app lives at `/opt/ixope`. You can update it over SSH:

```bash
# From your dev machine:
scp -r ixope/* root@<device-ip>:/opt/ixope/

# Or use git on the device:
cd /opt/ixope
git pull origin main

# Restart the app:
/etc/init.d/S99ixope restart
```

For production: mount `/opt/ixope` on a separate read-write partition
so the read-only rootfs stays clean.

---

## Data partition

Captured images, videos, logs, and preferences are stored on a separate
data partition mounted at `/var/ixope-data`. This partition is:
- **Read-write** (survives rootfs updates)
- **Separate** from the code (OTA can't wipe patient data)
- Created automatically on first boot

---

## Troubleshooting

### No display output
- Check kernel DTS matches your display panel
- Verify `CONFIG_DRM_ROCKCHIP=y` in kernel config
- Check `/var/ixope-data/logs/boot.log`

### No camera
- Verify `CONFIG_VIDEO_V4L2=y` and `CONFIG_VIDEO_USB_GSPCA=y`
- Check `ls /dev/video*` after boot

### WiFi not working
- Verify firmware: `BR2_PACKAGE_LINUX_FIRMWARE_BRCM_BCM43XXX=y`
- Check `nmcli dev status`

### App crashes
- Check logs: `cat /var/ixope-data/logs/boot.log`
- Test manually: `DISPLAY=:0 python3 -m ixope.app`

---

## Boot time optimization checklist

After the first working image, further reduce boot time:

- [ ] Build WiFi driver into kernel (not module): saves ~0.5s
- [ ] Use squashfs rootfs (read-only, faster mount): saves ~0.3s
- [ ] Remove htop/dropbear from production image
- [ ] Add kernel `initcall_blacklist=` for unused drivers
- [ ] Use eMMC instead of SD card: saves 2-3s
- [ ] Add U-Boot splash BMP for instant logo

---

## File structure

```
buildroot-external/
├── BUILD.md              ← this file
├── external.desc         ← Buildroot external tree descriptor
├── external.mk           ← package include
├── Config.in             ← package menu entries
├── configs/
│   └── ixope_rk3566_defconfig   ← main build config
├── board/ixope/
│   └── post-build.sh    ← rootfs customization script
├── package/ixope-app/
│   ├── Config.in         ← package description
│   └── ixope-app.mk     ← build/install recipe
└── rootfs-overlay/
    └── etc/
        └── init.d/
            └── S99ixope  ← app startup script
```
