# U-Boot Splash Logo

## Source File

The boot splash logo is stored at:

```
deploy/logo.bmp
```

This is a 480x480 24-bit uncompressed BMP file used directly by U-Boot.

## How It Gets to the Device

During the Buildroot build, `post-build.sh` copies:

```
deploy/logo.bmp → /boot/splash.bmp (on the rootfs)
```

U-Boot loads `/boot/splash.bmp` from the boot partition and displays it
on the DSI panel at ~0.5s after power-on, before the kernel starts.
The logo stays visible for 3 seconds.

## To Replace the Logo

Simply replace `deploy/logo.bmp` with a new 480x480 BMP file and rebuild.

Requirements:
- Format: BMP (uncompressed, 24-bit or 32-bit)
- Size: 480x480 pixels (matches DSI panel resolution)
- No conversion needed — file is used as-is
