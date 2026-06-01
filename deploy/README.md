# IXOPE Deployment Guide

## Boot Flow
```
Power ON → Linux Boot → Auto Login → X11 → autostart.sh → Medical UI Fullscreen
```
## Installation (Armbian / Radxa Zero 3W)

This section gives a step-by-step, copy-pasteable install for Armbian on Radxa Zero 3W.

1) Update OS and install base packages

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git python3 python3-pip python3-tk xorg openbox xinit unclutter
```

Optional (camera / numeric libs):
```bash
sudo apt install -y libatlas-base-dev libjpeg-dev
```

2) Clone repository into the expected path

```bash
mkdir -p /home/radxa/Documents
cd /home/radxa/Documents
git clone https://github.com/TheVasuA/ixope_device_1.git ixope
cd ixope
```

3) Install Python dependencies

```bash
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install -r requirements.txt
```

4) Make autostart script executable

```bash
chmod +x deploy/autostart.sh
```

5) Choose a startup method

Option A — systemd service (recommended):

```bash
sudo cp deploy/ixope.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ixope
sudo systemctl start ixope
```

Option B — `.xinitrc` (kiosk via X):

```bash
echo "exec /home/radxa/Documents/ixope/deploy/autostart.sh" >> /home/radxa/.xinitrc
```

6) Enable autologin for console → X (if using `.xinitrc`)

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin radxa --noclear %I $TERM
EOF
sudo systemctl daemon-reload
```

7) Performance tuning (optional)

- Disable swap if RAM allows:

```bash
sudo swapoff -a
sudo systemctl disable dphys-swapfile
```

- Reduce console noise / hide cursor via kernel or X settings; see deploy `autostart.sh`.

8) Boot splash GIF

Copy your boot GIF to the deployment folder to show it during startup:

```bash
cp /path/to/boot_logo.gif deploy/boot_logo.gif
```

9) Reboot and verify

```bash
sudo reboot

# After reboot, check service and logs:
sudo systemctl status ixope
sudo journalctl -u ixope -f
```

## OTA updater, CI and restart behavior

- The app contains a Git-based OTA updater that runs inside the app and checks `origin/main` every `UPDATE_CHECK_INTERVAL_MINUTES` (default 60) defined in `ixope/config/settings.py`.
- Workflow on update:
  1. `git fetch origin main` and compare revisions
  2. `git reset --hard <remote_rev>` to update working tree
  3. Install Python requirements: `python -m pip install -r requirements.txt`
  4. Run health checks (`python -m py_compile` over the repo)
  5. If health check passes and `AUTO_RESTART_ON_UPDATE` is enabled, the device runs `systemctl restart ixope` to start the new code
  6. If any step fails, the updater rolls back to the previous commit and reinstalls the previous requirements

## GitHub Actions CI

- A CI workflow is included at `.github/workflows/ci.yml` and runs on `push`/`pull_request` to `main`.
- It installs `requirements.txt` and runs `python -m compileall` to catch syntax errors before code reaches devices.

## Testing OTA manually (recommended first test)

1. Make a small change in the repo (e.g., bump `VERSION`) and push to `main`.
2. On device (or via SSH):

```bash
cd /home/radxa/Documents/ixope
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
# If different, apply update:
git reset --hard origin/main
sudo python3 -m pip install -r requirements.txt
python3 -m py_compile $(find . -name '*.py')
sudo systemctl restart ixope
```

3. Inspect logs if something fails:

```bash
sudo journalctl -u ixope -n 200
cat logs/ixope.log
```

## Recommended next steps for production

1. Configure device SSH deploy key for passwordless `git fetch`:
   - Generate `ssh-keygen -t ed25519 -f ~/.ssh/ixope_deploy -N ""`
   - Add `~/.ssh/ixope_deploy.pub` to repository Deploy Keys (read-only if only pulling)
2. Keep CI strict: add unit tests / integration tests to the GitHub Actions workflow.
3. Optionally enable device-level monitoring and remote shell access for recovery.

---

If you want, I can update this file with additional board-specific display/touchscreen setup instructions for Radxa Zero 3W.
```
