# IXOPE Project — Quick Reference (All Critical Numbers & Links)

## Hardware
- Board: Radxa Zero 3W (RK3566, 4GB LPDDR4, eMMC/SD)
- SoC: Rockchip RK3566 (Cortex-A55 quad-core)
- RAM: 4GB LPDDR4 @ 1056MHz
- WiFi: AIC8800D80 (SDIO, VID:0xC8A1 DID:0x0082/0x0182, chip rev 7)
- Display: ST7701S 480x480 round MIPI DSI panel (DSI0)
- Touch: Goodix GT911 I2C (addr 0x5d or 0x14, on I2C3)
- Camera: USB UVC endoscope (SF5A162, 640x480 YUYV)
- MCU: STM32 via UART1 (/dev/ttyS1, 9600 baud) — LED + focus control
- Debug console: /dev/ttyS2 (pins 8/10, 1500000 baud)
- GPU: Mali G52 (Panfrost driver)
- PMIC: RK8170

## Git Repos
- IXOPE App: https://github.com/TheVasuA/ixope_device_1.git (branch: main)
- Buildroot: https://github.com/buildroot/buildroot.git (tag: 2024.02)
- Kernel: https://github.com/radxa/kernel.git (branch: linux-5.10-gen-rkr8-buildroot)
- AIC8800 WiFi: https://github.com/radxa-pkg/aic8800.git (commit: 6ec370a)
- Radxa docs: https://docs.radxa.com/en/zero/zero3/other-os/buildroot

## Versions
- Kernel: 5.10.209 (Radxa BSP rkr8)
- U-Boot: 2024.01 (defconfig: radxa-cm3-io-rk3566)
- Buildroot: 2024.02
- Python: 3.11.8
- OpenCV: 4.9.0
- Pillow: python-pillow (BR2_PACKAGE_PYTHON_PILLOW)
- Tcl: 8.6, Tk: 8.6
- NetworkManager: 1.44.2

## Critical Build Fixes (apply every fresh build)
1. PATH fix: `export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`
2. Python symlink: `sudo ln -s /usr/bin/python3 /usr/bin/python`
3. Tkinter enable: `sed -i 's/--disable-tk/--enable-tk/g' package/python3/python3.mk`
4. OpenCV JPEG/PNG: BR2_PACKAGE_OPENCV4_WITH_JPEG=y, BR2_PACKAGE_OPENCV4_WITH_PNG=y
5. Kernel headers: BR2_KERNEL_HEADERS_5_10=y (NOT custom git for headers)
6. pyelftools: BR2_TARGET_UBOOT_NEEDS_PYELFTOOLS=y

## WiFi (AIC8800D80)
- Firmware path: /lib/firmware/aic8800D80/
- CRITICAL: symlink firmware files into /lib/firmware/ root (request_firmware doesn't search subdirs)
- Driver modules: aic8800_bsp.ko, aic8800_fdrv.ko (in /lib/modules/5.10.209/extra/)
- Load order: aic8800_bsp first, then aic8800_fdrv
- Firmware files needed: fw_patch_table_8800d80_u02.bin, fmacfw_8800d80_u02.bin, fw_adid_8800d80_u02.bin
- Config: CONFIG_USE_FW_REQUEST=y in module build opts

## UART Protocol (STM32)
- Port: /dev/ttyS1 @ 9600 baud
- LED cmd: *XY# (X=LED 1-6, Y=brightness 0-9) e.g. *55# = LED5 at 50%
- All off: OF
- Focus: L24 to L70 (liquid lens 0-100%)
- Battery read: MCU sends B5%, B25%, B100%

## Key Config Files
- Defconfig: buildroot-external/configs/ixope_rk3566_defconfig
- Kernel fragment: buildroot-external/board/ixope/linux.fragment
- U-Boot fragment: buildroot-external/board/ixope/uboot.fragment
- Device tree: rk3566-radxa-zero-3w-ap6212.dtb (stock, DSI disabled)
- Post-build: buildroot-external/board/ixope/post-build.sh
- Boot blobs: buildroot-external/board/ixope/download-blobs.sh
- SD image: buildroot-external/board/ixope/create-sdcard-image.sh
- Boot logo: deploy/logo.bmp (480x480, copied to /boot/splash.bmp)

## Init Scripts (boot order)
- S00dmesg — suppress kernel console
- S01cpufreq — performance governor
- S01splash — framebuffer splash text
- S10modules — load aic8800_bsp + aic8800_fdrv
- S45network — dbus + NetworkManager + NTP sync (15s delay)
- S50xorg — X server on fb0
- S99ixope — python3 /opt/ixope/app.py

## Build Commands (WSL2 Ubuntu 22.04 on D:\WSL\Ubuntu2204)
```
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd ~/buildroot
export BR2_EXTERNAL=~/ixope/buildroot-external
make ixope_rk3566_defconfig
make -j$(nproc)
bash ~/ixope/buildroot-external/board/ixope/create-sdcard-image.sh ~/buildroot/output/images
cp ~/buildroot/output/images/ixope-sdcard.img.gz /mnt/d/
```

## Flash
- SD card: Balena Etcher → D:\ixope-sdcard.img.gz
- eMMC: rkdeveloptool (Maskrom mode: hold BOOT button)

## Known Issues & Workarounds
- DSI panel: disabled in stock DTB, needs custom DTS overlay to enable
- Video recording: h264_v4l2m2m not available, needs software codec or kernel RGA driver
- System time: no RTC battery, clock resets on boot → NTP syncs after WiFi connects
- Tkinter canvas crash: "invalid command name .!canvas" — animation callback fires after window destroy
- Gallery re-open: cache cleared on close() to prevent stale PhotoImage refs
