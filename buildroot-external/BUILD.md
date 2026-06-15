# IXOPE Buildroot Image — Complete Build & Flash Guide

## Overview

Builds a minimal Linux image for the Radxa Zero 3W that boots directly
to the IXOPE medical camera application in **~5 seconds** (eMMC) / **~7 seconds** (SD).

**What's included:** Linux kernel + Python 3 + OpenCV + Pillow + Flask + Tkinter +
X11 (minimal) + WiFi (NetworkManager) + I2C tools + your IXOPE app. Nothing else.

---

## You need TWO machines

1. **Build machine** — Linux PC (Ubuntu 22.04+) or WSL2 on Windows. Compiles the image.
2. **Radxa Zero 3W** — the target device where you flash the image.

---

## Step 1: Install build tools (one-time, on build machine)

```bash
sudo apt update
sudo apt install -y \
    build-essential gcc g++ make git wget curl unzip bc \
    libncurses-dev flex bison libssl-dev libelf-dev \
    python3 python3-dev file cpio rsync dosfstools mtools \
    device-tree-compiler u-boot-tools
```

---

## Step 2: Clone Buildroot + your code

```bash
cd ~
git clone https://github.com/buildroot/buildroot.git
git clone https://github.com/TheVasuA/ixope_device_1.git ixope

cd buildroot
git checkout 2024.02
```

---

## Step 3: Set the external tree path

```bash
export BR2_EXTERNAL=~/ixope/buildroot-external
```

---

## Step 4: Load the IXOPE config

```bash
make ixope_rk3566_defconfig
```

---

## Step 5: Build the image

```bash
make -j$(nproc)
```

**First build: ~45-90 minutes** (downloads toolchain + all packages).
**Subsequent builds: ~5-10 minutes** (only rebuilds changes).

Output files at `~/buildroot/output/images/`:
```
├── Image                       (Linux kernel)
├── rootfs.ext4                 (root filesystem)
├── u-boot-rockchip.bin         (bootloader)
└── rk3566-radxa-zero-3w.dtb    (device tree)
```

---

## Step 6: Flash to the device

### Option A: Flash to SD card (easiest to start)

```bash
# Insert SD card into your build machine
# Find the device name:
lsblk
# Example: /dev/sdb (NEVER use /dev/sda — that's your PC!)

# Clear existing partition table
sudo dd if=/dev/zero of=/dev/sdX bs=1M count=1
sudo parted /dev/sdX mklabel gpt

# Write U-Boot (raw, at sector 64 = 32KB offset)
sudo dd if=output/images/u-boot-rockchip.bin of=/dev/sdX seek=64 conv=notrunc

# Create rootfs partition (16MB to 272MB)
sudo parted /dev/sdX mkpart rootfs ext4 16MiB 272MiB

# Create data partition (272MB to end of card)
sudo parted /dev/sdX mkpart data ext4 272MiB 100%

# Write rootfs to partition 2
sudo dd if=output/images/rootfs.ext4 of=/dev/sdX2 bs=4M status=progress

# Format data partition
sudo mkfs.ext4 -L ixope-data /dev/sdX3

sync
```

Eject SD card → insert into Radxa → power on.

### Option B: Flash to eMMC (faster boot — recommended)

1. **Enter Maskrom mode on the Radxa:**
   - Hold the **BOOT button** on the board
   - Connect USB-C cable to your PC while holding the button
   - Release after 3 seconds
   - The device appears as a USB Rockchip device

2. **Install flash tools:**
```bash
sudo apt install -y rkdeveloptool
```

3. **Download the DDR init blob:**
```bash
wget https://dl.radxa.com/rock3/images/loader/rk356x_spl_loader_ddr1056_v1.12.109.bin
```

4. **Flash:**
```bash
# Check device is detected
rkdeveloptool ld

# Initialize DDR
rkdeveloptool db rk356x_spl_loader_ddr1056_v1.12.109.bin

# Flash U-Boot (at sector 64)
rkdeveloptool wl 64 output/images/u-boot-rockchip.bin

# Flash rootfs (at sector 32768 = 16MB offset)
rkdeveloptool wl 32768 output/images/rootfs.ext4

# Reboot the device
rkdeveloptool rd
```

---

## Step 7: First boot

Power on the Radxa. Expected boot sequence:

```
0.0s  Power on
0.5s  U-Boot loads kernel
2.0s  Kernel boots (quiet, built-in drivers)
2.5s  BusyBox init starts
3.0s  X server starts
4.0s  Python loads the app
5.0s  Camera feed visible on screen
```

---

## Step 8: Connect via SSH (for debugging/updates)

The image includes `dropbear` SSH server (no password by default).

```bash
# Find device IP (from the app's WiFi page, or from your router)
ssh root@<device-ip>
```

---

## Updating the app after first flash

You do NOT need to rebuild the whole image to update the app code:

```bash
# From your dev machine — push code over SSH:
scp -r ~/ixope/* root@<device-ip>:/opt/ixope/

# Or use git on the device:
ssh root@<device-ip>
cd /opt/ixope
git pull origin main

# Restart the app:
/etc/init.d/S99ixope restart
```

---

## WiFi setup (first time)

After boot, use the app's WiFi icon to scan and connect. Or via SSH:

```bash
nmcli dev wifi connect "YourSSID" password "YourPassword"
```

---

## Data partition

All runtime data is stored separately from the code:

| Path | Content |
|------|---------|
| `/opt/ixope/` | App code (read-only in production) |
| `/var/ixope-data/logs/` | Application logs |
| `/var/ixope-data/captured_images/` | Patient images |
| `/var/ixope-data/recorded_videos/` | Recorded videos |
| `/var/ixope-data/prefs.json` | User preferences |

The data partition survives app updates and rootfs reflashes.

---

## (Optional) Customize the build

```bash
# General settings (packages, init system, etc.)
make menuconfig

# Kernel config (add/remove hardware drivers)
make linux-menuconfig

# Save your changes back to the defconfig:
make savedefconfig
cp output/defconfig ~/ixope/buildroot-external/configs/ixope_rk3566_defconfig
```

**Important kernel options to verify:**
- `CONFIG_VIDEO_V4L2=y` — USB camera
- `CONFIG_I2C_RK3X=y` — I2C for LED controller
- `CONFIG_SERIAL_8250=y` — UART
- `CONFIG_DRM_ROCKCHIP=y` — Display output
- `CONFIG_BRCMFMAC=y` — WiFi (built-in, not module)

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No display output | Verify DTS name matches your board: `rk3566-radxa-zero-3w` |
| No camera | Check `ls /dev/video*` — add V4L2 to kernel if missing |
| No WiFi | Verify firmware: `BR2_PACKAGE_LINUX_FIRMWARE_BRCM_BCM43XXX=y` |
| App crashes | Check `/var/ixope-data/logs/boot.log` |
| Black screen | Connect USB serial (115200 baud) to see boot messages |
| Kernel panic | Wrong DTS or missing rootfs — check U-Boot env |

---

## Boot time optimization (after first working image)

- [ ] Use **eMMC** instead of SD card (saves 2-3s)
- [ ] Build WiFi driver **into** kernel (not as module)
- [ ] Switch to **squashfs** rootfs (read-only, faster mount)
- [ ] Add **U-Boot splash** BMP for instant logo at 0.5s
- [ ] Remove dropbear/htop from production builds
- [ ] Add `initcall_blacklist=` for unused kernel drivers

---

## TL;DR — 6 commands from zero to image

```bash
sudo apt install -y build-essential git wget libncurses-dev flex bison libssl-dev python3 file cpio rsync
cd ~ && git clone https://github.com/buildroot/buildroot.git && git clone https://github.com/TheVasuA/ixope_device_1.git ixope
cd buildroot && git checkout 2024.02
export BR2_EXTERNAL=~/ixope/buildroot-external
make ixope_rk3566_defconfig
make -j$(nproc)
```

Then flash `output/images/*` to SD card or eMMC using the steps above.

---

## File structure

```
buildroot-external/
├── BUILD.md                          ← this file
├── external.desc                     ← Buildroot external tree descriptor
├── external.mk                       ← package includes
├── Config.in                         ← package menu entries
├── configs/
│   └── ixope_rk3566_defconfig        ← main build configuration
├── board/ixope/
│   └── post-build.sh                 ← rootfs customization script
├── package/ixope-app/
│   ├── Config.in                     ← package description
│   └── ixope-app.mk                  ← build/install recipe
└── rootfs-overlay/
    └── etc/init.d/
        └── S99ixope                  ← app startup script (runs on boot)
```
