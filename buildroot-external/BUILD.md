# IXOPE Buildroot Image — Official Radxa Zero 3W BSP

## Overview

Builds a minimal Linux image for the **Radxa Zero 3W** (RK3566) using the
**official Radxa BSP kernel 5.10** (`linux-5.10-gen-rkr8-buildroot`).

Boot to IXOPE app in **~5 seconds** (eMMC) / **~7 seconds** (SD card).

**Key specs:**
- Official Radxa kernel: `https://github.com/radxa/kernel.git` branch `linux-5.10-gen-rkr8-buildroot`
- ST7701S 480x480 round MIPI DSI panel + HDMI output
- Goodix GT911 I2C touchscreen
- WiFi BCM43430/AP6212 (built-in, not module)
- USB camera via V4L2
- Python 3 + OpenCV + Tkinter + Flask

---

## TL;DR — Build in 6 commands

```bash
# 1. Install build tools (Ubuntu 22.04+)
sudo apt install -y build-essential gcc g++ make git wget curl unzip bc \
    libncurses-dev flex bison libssl-dev libelf-dev \
    python3 python3-dev file cpio rsync dosfstools mtools parted \
    device-tree-compiler u-boot-tools gzip

# 2. Clone
cd ~
git clone https://github.com/buildroot/buildroot.git
git clone https://github.com/TheVasuA/ixope_device_1.git ixope
cd buildroot && git checkout 2024.02

# 3. Configure
export BR2_EXTERNAL=~/ixope/buildroot-external
make ixope_rk3566_defconfig

# 4. Build (first time: 45-90 min)
make -j4

# 5. Create flashable image
bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh ~/buildroot/output/images

# 6. Copy to Windows (if building in WSL2)
cp ~/buildroot/output/images/ixope-sdcard.img.gz /mnt/d/
```

Flash with **Balena Etcher** → insert SD → power on → app in ~5s.

---

## Kernel Source

The kernel is fetched directly by Buildroot from:

```
Repository: https://github.com/radxa/kernel.git
Branch:     linux-5.10-gen-rkr8-buildroot
Defconfig:  rockchip_linux
Fragment:   board/ixope/linux.fragment (adds DSI, touchscreen, camera, WiFi)
```

This is the **official Radxa Zero 3W BSP** — all hardware (WiFi, GPU, USB, display)
is validated and supported.

---

## U-Boot

Uses `radxa-zero-3-rk3566` defconfig with our fast-boot fragment:
- Zero boot delay
- No USB/network/SCSI scanning
- Boots directly via extlinux.conf from MMC

---

## Device Tree

`board/ixope/rk3566-radxa-zero-3w-ixope.dts` includes the official
`rk3566-radxa-zero-3w.dts` as base and adds:
- ST7701S 480x480 MIPI DSI panel on DSI0
- Panel power rails (VCI 2.8V, IOVCC 1.8V)
- Goodix GT911 touchscreen on I2C3
- VOP2 VP1 → DSI0 routing

---

## Boot Sequence

```
0.0s  Power on
0.5s  U-Boot → splash logo on DSI panel
2.0s  Kernel boots (quiet, built-in drivers)
2.5s  BusyBox init (parallel scripts)
3.0s  X server starts on DSI panel
4.0s  Python loads IXOPE app
5.0s  Camera feed visible on 480x480 display
```

---

## Flash to SD Card

```bash
# Linux
gunzip ixope-sdcard.img.gz
sudo dd if=ixope-sdcard.img of=/dev/sdX bs=4M status=progress

# Windows — use Balena Etcher (drag .img.gz directly)

# Mac
gunzip ixope-sdcard.img.gz
sudo dd if=ixope-sdcard.img of=/dev/diskN bs=4m
```

---

## Flash to eMMC (faster boot)

```bash
# Enter Maskrom mode: hold BOOT button → connect USB → release
sudo apt install -y rkdeveloptool
wget https://dl.radxa.com/rock3/images/loader/rk356x_spl_loader_ddr1056_v1.12.109.bin

rkdeveloptool ld
rkdeveloptool db rk356x_spl_loader_ddr1056_v1.12.109.bin
rkdeveloptool wl 64 output/images/u-boot-rockchip.bin
rkdeveloptool wl 32768 output/images/rootfs.ext4
rkdeveloptool rd
```

---

## Update App (no rebuild needed)

```bash
scp -r ~/ixope/* root@<device-ip>:/opt/ixope/
ssh root@<device-ip> "/etc/init.d/S99ixope restart"
```

---

## Customize

```bash
make menuconfig              # packages
make linux-menuconfig        # kernel drivers
make savedefconfig
cp output/defconfig ~/ixope/buildroot-external/configs/ixope_rk3566_defconfig
```

---

## File Structure

```
buildroot-external/
├── BUILD.md                          ← this file
├── external.desc                     ← tree name: IXOPE
├── external.mk                       ← package includes
├── Config.in                         ← package menu
├── configs/
│   └── ixope_rk3566_defconfig        ← main config
├── board/ixope/
│   ├── rk3566-radxa-zero-3w-ixope.dts  ← device tree (DSI + touch)
│   ├── linux.fragment                ← kernel config additions
│   ├── uboot.fragment                ← fast-boot config
│   ├── boot.cmd                      ← boot script (fallback)
│   ├── post-build.sh                 ← rootfs optimization
│   └── create-sdcard-image.sh        ← image builder
├── package/ixope-app/
│   ├── Config.in
│   └── ixope-app.mk
└── rootfs-overlay/
    ├── etc/init.d/
    │   ├── S01splash                 ← boot splash
    │   └── S99ixope                  ← app startup
    └── opt/ixope/
        └── splash.py                 ← Tkinter splash screen
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No display output | Check DSI panel wiring, verify DTS reset GPIO |
| No touchscreen | Verify I2C3 address (0x5d or 0x14 for Goodix) |
| No camera | `ls /dev/video*` — UVC driver should be built-in |
| No WiFi | Check firmware symlink in /lib/firmware/brcm/ |
| Kernel panic | Wrong DTS or missing rootfs partition |
| Boot slow (>10s) | Check if USB scanning is disabled in U-Boot |
