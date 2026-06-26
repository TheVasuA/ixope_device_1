# IXOPE Buildroot Image — Radxa Zero 3W (RK3566)

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

**Reference:** [Radxa Zero 3 Buildroot docs](https://docs.radxa.com/en/zero/zero3/other-os/buildroot)

---

## Step 1: Install WSL2 Ubuntu 22.04 on D: Drive

> Windows 10/11 — run all commands in **PowerShell (Admin)**

```powershell
# Enable WSL if not already
wsl --install --no-distribution

# Download and install Ubuntu 22.04 (default location)
wsl --install -d Ubuntu-22.04 --no-launch

# Export and re-import to D: drive
mkdir D:\WSL\Ubuntu2204
wsl --export Ubuntu-22.04 D:\WSL\ubuntu2204.tar
wsl --unregister Ubuntu-22.04
wsl --import Ubuntu2204 D:\WSL\Ubuntu2204 D:\WSL\ubuntu2204.tar

# Clean up tarball
del D:\WSL\ubuntu2204.tar

# Launch
wsl -d Ubuntu2204
```

Inside WSL, create your build user:

```bash
adduser builder
usermod -aG sudo builder
echo -e "[user]\ndefault=builder" >> /etc/wsl.conf
exit
```

Restart WSL and enter as `builder`:

```powershell
wsl --shutdown
wsl -d Ubuntu2204
```

---

## Step 2: Install Build Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential gcc g++ make git wget curl unzip bc \
    libncurses-dev flex bison libssl-dev libelf-dev \
    python3 python3-dev file cpio rsync dosfstools mtools parted \
    device-tree-compiler u-boot-tools gzip lz4 fakeroot bsdmainutils
```

---

## Step 3: Clone Repositories

```bash
cd ~

# Buildroot (use 2024.02 LTS)
git clone https://github.com/buildroot/buildroot.git
cd buildroot && git checkout 2024.02 && cd ~

# IXOPE project
git clone https://github.com/TheVasuA/ixope_device_1.git ixope
```

> **Alternative:** If you already have the ixope repo on Windows at `D:\infiniti\medical\ixope`, symlink it:
> ```bash
> ln -s /mnt/d/infiniti/medical/ixope ~/ixope
> ```

---

## Step 4: Download Boot Blobs (One-Time)

```bash
bash ~/ixope/buildroot-external/board/ixope/download-blobs.sh
```

This fetches from Rockchip's rkbin repository:
- `ddr.bin` — DDR init binary for RK3566
- `bl31.elf` — ARM Trusted Firmware BL31

---

## Step 5: Configure Buildroot

```bash
cd ~/buildroot
export BR2_EXTERNAL=~/ixope/buildroot-external
make ixope_rk3566_defconfig
```

This loads the full configuration including:
- Kernel from `https://github.com/radxa/kernel.git` branch `linux-5.10-gen-rkr8-buildroot`
- U-Boot with fast-boot fragment
- All packages (Python 3, OpenCV, Flask, Tkinter, etc.)
- Custom device tree for DSI panel + touchscreen

---

## Step 6: Build (First Time ~45-90 min)

```bash
make -j$(nproc)
```

Buildroot automatically:
1. Downloads the Radxa kernel source
2. Applies `linux.fragment` config additions
3. Compiles kernel with `rockchip_linux` defconfig
4. Builds U-Boot with `radxa-zero-3-rk3566` defconfig + `uboot.fragment`
5. Builds all userspace packages
6. Assembles the root filesystem

---

## Step 7: Create Flashable SD Card Image

```bash
bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh ~/buildroot/output/images
```

Output: `~/buildroot/output/images/ixope-sdcard.img.gz`

---

## Step 8: Copy to Windows & Flash

```bash
cp ~/buildroot/output/images/ixope-sdcard.img.gz /mnt/d/
```

On Windows:
1. Open **Balena Etcher**
2. Select `D:\ixope-sdcard.img.gz`
3. Select SD card
4. Flash

Insert SD → power on → app running in ~5 seconds.

---

## Rebuild After Changes

```bash
cd ~/buildroot

# Rebuild just the app package
make ixope-app-rebuild

# Full rebuild
make -j$(nproc)

# Recreate image
bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh ~/buildroot/output/images

# Copy to Windows
cp ~/buildroot/output/images/ixope-sdcard.img.gz /mnt/d/
```

---

## Update App on Device (No Rebuild)

```bash
scp -r ~/ixope/* root@<device-ip>:/opt/ixope/
ssh root@<device-ip> "/etc/init.d/S99ixope restart"
```

---

## Customize Kernel / Packages

```bash
cd ~/buildroot

# Edit packages
make menuconfig

# Edit kernel config
make linux-menuconfig

# Save changes
make savedefconfig
cp output/defconfig ~/ixope/buildroot-external/configs/ixope_rk3566_defconfig
```

---

## Kernel Development (Optional — Standalone)

Only needed if you want to patch or debug the kernel source outside Buildroot:

```bash
cd ~
git clone https://github.com/radxa/kernel.git
cd kernel
git remote add radxa https://github.com/radxa/kernel.git
git fetch radxa
git switch -c linux-5.10-gen-rkr8-buildroot radxa/linux-5.10-gen-rkr8-buildroot
```

Reference: [Radxa Zero 3 Buildroot docs](https://docs.radxa.com/en/zero/zero3/other-os/buildroot)

> **Note:** For normal builds, Buildroot handles kernel fetching automatically.
> These commands are only for direct kernel source work.

---

## Flash to eMMC (Faster Boot)

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

## Boot Splash Logo (3 seconds)

U-Boot displays the logo on the DSI panel immediately at power-on and holds
it for 3 seconds before loading the kernel. The screen is never blank.

**Logo file:** `deploy/logo.bmp` (480x480 BMP, already in the repo)

The `post-build.sh` script automatically copies `deploy/logo.bmp` → `/boot/splash.bmp`
during the build. No manual conversion needed.

**What U-Boot does:**
```
1. Load /boot/splash.bmp from SD/eMMC partition 1
2. Display BMP on DSI panel (video enabled via uboot.fragment)
3. Sleep 3 seconds (logo stays visible)
4. Load kernel via extlinux.conf → normal boot continues
```

---

## Boot Sequence (with splash)

```
0.0s  Power on → DDR init (ddr.bin)
0.3s  BL31 → U-Boot starts
0.5s  U-Boot loads splash.bmp → LOGO VISIBLE on DSI panel
0.5s─3.5s  Logo displayed (3 second hold)
3.5s  Kernel loading begins
4.5s  Kernel booted (quiet, built-in drivers)
5.0s  BusyBox init → X server → IXOPE app
6.0s  Camera feed visible
```

---

## Key Understanding Points

### How the Build System Works

```
┌─────────────────────────────────────────────────────────┐
│  Buildroot (vanilla 2024.02)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  BR2_EXTERNAL = ~/ixope/buildroot-external        │  │
│  │  (our custom board, packages, overlays)           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Automatically fetches:                                 │
│  • Kernel from github.com/radxa/kernel.git             │
│    branch: linux-5.10-gen-rkr8-buildroot               │
│  • U-Boot from upstream + our defconfig/fragment       │
│  • All packages (Python, OpenCV, etc.)                 │
└─────────────────────────────────────────────────────────┘
```

### What Each Config File Controls

| File | Purpose |
|------|---------|
| `ixope_rk3566_defconfig` | Master config — kernel source, packages, build options |
| `linux.fragment` | Kernel config additions (DSI, touchscreen, camera, WiFi) |
| `uboot.fragment` | U-Boot config (splash, silent boot, no USB scan) |
| `post-build.sh` | Rootfs modifications after build (init scripts, fstab, splash copy) |
| `rk3566-radxa-zero-3w-ixope.dts` | Device tree (hardware: panel, touch, GPIOs) |
| `create-sdcard-image.sh` | Assembles final flashable .img |

### Build vs Official Radxa SDK

| | IXOPE Build (our approach) | Official Radxa SDK |
|--|--|--|
| Base | Vanilla Buildroot 2024.02 | Full Rockchip RK356x SDK (~10GB) |
| Config | `BR2_EXTERNAL` external tree | `./build.sh` with rockchip defconfigs |
| Kernel | Same (radxa/kernel.git `linux-5.10-gen-rkr8-buildroot`) | Same |
| Output | Raw `ixope-sdcard.img.gz` (dd/Etcher) | `update.img` (RK format, SDDiskTool) |
| Pros | Lightweight, reproducible, standard Buildroot docs | More hardware support out-of-box |
| Cons | Custom DTS/config needed | Large download, rockchip-specific tooling |

### U-Boot Splash — How It Works

1. **Video enabled in U-Boot** via `uboot.fragment` (`CONFIG_VIDEO=y`, `CONFIG_VIDEO_ROCKCHIP=y`)
2. U-Boot initializes the DSI panel (uses same DTS as kernel)
3. `CONFIG_BOOTCOMMAND` loads `/boot/splash.bmp` to memory
4. `bmp display` renders it to the panel framebuffer
5. `sleep 3` holds the image for 3 seconds
6. `sysboot` loads `extlinux.conf` and boots the kernel
7. Kernel re-initializes the panel — splash.py (Tkinter) shows until app is ready

### Kernel Branch Explained

```
Repository: https://github.com/radxa/kernel.git
Branch:     linux-5.10-gen-rkr8-buildroot
```

- **linux-5.10** — kernel version (LTS)
- **gen** — generic Rockchip (not board-specific)
- **rkr8** — Rockchip release 8 (their BSP patchset)
- **buildroot** — tailored for Buildroot (vs Android or Debian variants)

This is the official BSP from Radxa — all RK3566 hardware (VOP2, DSI, I2C, USB, WiFi)
is validated. Our `linux.fragment` just enables specific drivers for our peripherals.

Ref: [Radxa Zero 3 Buildroot docs](https://docs.radxa.com/en/zero/zero3/other-os/buildroot)

---

## Device Tree

`board/ixope/rk3566-radxa-zero-3w-ixope.dts` includes the official
`rk3566-radxa-zero-3w.dts` as base and adds:
- ST7701S 480x480 MIPI DSI panel on DSI0
- Panel power rails (VCI 2.8V, IOVCC 1.8V)
- Goodix GT911 touchscreen on I2C3
- VOP2 VP1 → DSI0 routing

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
│   ├── download-blobs.sh            ← fetch DDR + BL31 binaries
│   └── create-sdcard-image.sh        ← image builder
├── package/ixope-app/
│   ├── Config.in
│   └── ixope-app.mk
└── rootfs-overlay/
    ├── etc/init.d/
    │   ├── S01splash                 ← boot splash
    │   ├── S45network                ← network config
    │   ├── S50xorg                   ← X server
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
| WSL2 out of space | `wsl --manage Ubuntu2204 --set-sparse true` |
| Permission denied | Don't build as root; use `builder` user |
