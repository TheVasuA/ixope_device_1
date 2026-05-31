# IXOPE Deployment Guide

## Boot Flow
```
Power ON → Linux Boot → Auto Login → X11 → autostart.sh → Medical UI Fullscreen
```

## Installation

1. Copy the `ixope/` folder to `/home/radxa/Documents/tk_ixope/`
2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Set up autostart (choose one method):

### Method A: .desktop autostart
```bash
mkdir -p ~/.config/autostart
cp deploy/ixope.desktop ~/.config/autostart/
```

### Method B: systemd service
```bash
sudo cp deploy/ixope.service /etc/systemd/system/
sudo systemctl enable ixope
sudo systemctl start ixope
```

### Method C: .xinitrc
```bash
echo "exec /home/radxa/Documents/tk_ixope/deploy/autostart.sh" >> ~/.xinitrc
```

## Performance Tuning

### Kernel parameters (add to /boot/cmdline.txt or grub):
```
quiet splash vt.global_cursor_default=0
```

### Swap (disable if RAM > 512MB):
```bash
sudo swapoff -a
sudo systemctl disable dphys-swapfile
```

### GPU memory (if applicable):
```
gpu_mem=64

## Boot Splash and OTA

1. Place the boot logo GIF at `deploy/boot_logo.gif`.
   - The app shows this GIF during startup if it exists.
   - If the file is missing, a simple fallback splash screen is shown.

2. The application now includes a Git-based OTA updater.
   - It checks the configured `origin/main` branch for updates.
   - On update, it pulls the latest code, installs requirements, and validates Python syntax.
   - If the update fails, it automatically rolls back to the previous commit.
```
