# U-Boot boot script for IXOPE — fastest possible direct boot
# Compile with: mkimage -C none -A arm64 -T script -d boot.cmd boot.scr
#
# NO SPLASH in U-Boot. Text splash is done by kernel fbcon (S01splash).
# This saves 2-3s of video subsystem probing.

# Load compressed kernel + DTB from SD card (mmc 1, partition 1)
load mmc 1:1 0x02080000 /boot/Image.lz4
load mmc 1:1 0x0a100000 /boot/rk3566-radxa-zero-3w-ap6212.dtb

# Boot args — quiet, fast, no cursor, limited udev timeout
setenv bootargs root=/dev/mmcblk1p1 rootfstype=ext4 rootwait rw quiet loglevel=0 vt.global_cursor_default=0 consoleblank=0 udev.event_timeout=5 loop.max_loop=4 console=ttyS2,1500000

# Boot immediately
booti 0x02080000 - 0x0a100000
