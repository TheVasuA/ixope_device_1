# U-Boot Splash Logo

U-Boot requires a **BMP** file for splash display.

## How to create the splash BMP

Convert your `boot_logo.gif` to an uncompressed 480x480 BMP:

```bash
# On your build machine:
convert deploy/boot_logo.gif -resize 480x480 -type TrueColor BMP3:buildroot-external/board/ixope/splash.bmp
```

Or using Python/Pillow:

```python
from PIL import Image
img = Image.open("deploy/boot_logo.gif")
img = img.resize((480, 480))
img.save("buildroot-external/board/ixope/splash.bmp", "BMP")
```

The splash.bmp must be placed in the rootfs at `/boot/splash.bmp` (done by post-build.sh).

## How it works

U-Boot loads the BMP from the boot partition and draws it to the display
at about 0.5 seconds after power-on — before the kernel even starts.
This ensures the screen is never blank.
