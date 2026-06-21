# U-Boot boot script for IXOPE — splash logo + immediate kernel load
# Compile with: mkimage -C none -A arm64 -T script -d boot.cmd boot.scr

# No USB scan, no delays — boot immediately
setenv bootdelay 0
usb stop

# Show splash logo immediately (BMP at /boot/splash.bmp on the rootfs partition)
if load mmc 0:2 ${loadaddr} /boot/splash.bmp; then
    bmp display ${loadaddr}
fi

# Load kernel
load mmc 0:2 ${kernel_addr_r} /boot/Image

# Load device tree
load mmc 0:2 ${fdt_addr_r} /boot/rk3566-radxa-zero-3w.dtb

# Boot args: quiet, fast, no console spam
setenv bootargs "root=/dev/mmcblk0p2 rootfstype=ext4 rootwait ro quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 plymouth.enable=0 raid=noautodetect"

# Boot immediately
booti ${kernel_addr_r} - ${fdt_addr_r}
