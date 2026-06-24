# U-Boot boot script for IXOPE — fast direct boot, no scanning
# Compile with: mkimage -C none -A arm64 -T script -d boot.cmd boot.scr
#
# This is a FALLBACK if extlinux.conf is not found.
# Primary boot method is via extlinux.conf (set in uboot.fragment).

# Load kernel + DTB from SD card (mmc 1, partition 1)
load mmc 1:1 0x02080000 /boot/Image
load mmc 1:1 0x0a100000 /boot/rk3566-radxa-zero-3w-ap6212.dtb

# Boot args — quiet, fast, no cursor, DSI panel primary
setenv bootargs root=/dev/mmcblk1p1 rootfstype=ext4 rootwait rw quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 console=ttyS2,1500000

# Boot immediately
booti 0x02080000 - 0x0a100000
