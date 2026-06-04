# IXOPE Fast Boot — get the GUI up quickly with a logo from the start

Linux can't boot "instantly," but a 40s boot on a Radxa Zero 3W is almost always
caused by a few slow services (usually a network-wait) plus booting into a full
desktop. This guide gets you to roughly **12-18s to GUI**, with a **logo on
screen within ~2-4s** so the panel is never blank.

Boot flow we are building:

```
Power ON
  → Kernel + panel driver        (logo appears here, via fbi)
  → multi-user.target (no desktop)
  → autologin on tty1 → startx
  → .xinitrc → python3 -m ixope.app   (app splash replaces logo seamlessly)
```

---

## 0. Measure first (always)

```bash
systemd-analyze                 # kernel vs userspace split
systemd-analyze blame           # slowest units, worst first
systemd-analyze critical-chain  # what is actually on the critical path
```

Optimize the top offenders from `blame`/`critical-chain`. Don't disable things
blindly.

---

## 1. Remove the biggest time sinks

The classic 15-30s culprit is a "wait for network online" service. The app
connects Wi-Fi asynchronously, so the boot must NOT block on it:

```bash
sudo systemctl disable NetworkManager-wait-online.service
sudo systemctl disable systemd-networkd-wait-online.service 2>/dev/null
```

Other services a medical kiosk usually doesn't need at boot:

```bash
sudo systemctl disable ModemManager.service bluetooth.service cups.service \
    dphys-swapfile.service snapd.service \
    apt-daily.timer apt-daily-upgrade.timer 2>/dev/null
```

(Keep anything you actually use. Re-check with `systemd-analyze blame`.)

---

## 2. Stop booting into a desktop

A display manager + desktop environment is slow. Boot to the text target and
start a bare X session yourself:

```bash
sudo systemctl set-default multi-user.target
```

---

## 3. Autologin on tty1, then startx

Create an autologin drop-in for tty1:

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf >/dev/null <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin radxa --noclear %I $TERM
EOF
sudo systemctl daemon-reload
```

Make the login shell launch X on tty1 only. Append to `/home/radxa/.bash_profile`
(or `.profile`):

```bash
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
```

Install the minimal X session file:

```bash
cp /home/radxa/Documents/ixope/deploy/xinitrc /home/radxa/.xinitrc
```

`.xinitrc` execs `python3 -m ixope.app` directly — no window manager, no
desktop. That is the fastest path to the Tkinter UI.

> Note: this replaces the systemd `ixope.service` approach. Use ONE method.
> If you previously enabled `ixope.service`, disable it:
> `sudo systemctl disable ixope.service`

---

## 4. Show the logo as early as possible

Install `fbi` and the early-logo service:

```bash
sudo apt install -y fbi
sudo cp /home/radxa/Documents/ixope/deploy/ixope-bootlogo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ixope-bootlogo.service
```

This draws `deploy/boot_logo.gif` straight to the framebuffer very early, and
`.xinitrc` kills `fbi` right before the app starts so the app's own Tkinter
splash takes over with no black flash in between.

### Which framebuffer?
Check what your 480x480 panel exposes:

```bash
ls /dev/fb*            # usually /dev/fb0; could be /dev/fb1 for SPI panels
cat /sys/class/graphics/fb0/name
```

If it's `fb1`, edit `-d /dev/fb0` → `-d /dev/fb1` in the service.

### SPI / userspace-driven panel?
If the panel only lights up after a kernel module loads, the logo can't appear
before that. Order the logo service after it, e.g. add to the `[Unit]` section:

```
After=systemd-modules-load.service
```

or add a `udev` settle. For a DRM/KMS panel that comes up with the kernel, you
can alternatively use **Plymouth** for an even earlier, flicker-free splash.

---

## 5. Optional kernel-level trims

- Quiet kernel + no cursor (faster, cleaner): add to the kernel cmdline
  (Armbian: `/boot/armbianEnv.txt` `extraargs=`):
  ```
  quiet loglevel=0 vt.global_cursor_default=0
  ```
- Faster rootfs check: ensure you're not fsck-ing every boot.
- If RAM allows, disable swap (already covered by disabling dphys-swapfile).

---

## 6. Verify

```bash
sudo reboot
# after reboot:
systemd-analyze            # confirm the new, lower number
systemctl --failed         # make sure nothing you disabled broke a dependency
```

Expected: logo within a few seconds, GUI in ~12-18s depending on the SD card /
eMMC speed and panel driver. eMMC is noticeably faster than an SD card here —
if you're on SD and need every second, that's the next biggest win.

---

## App-side note

`app.py` is already boot-optimized: it disables GC during startup, raises
process priority (`nice -10`), and preloads the heavy camera/LED/network/storage
modules in a background thread *while the splash is visible*, so the UI is
responsive the moment it appears. No app changes are needed for fast boot — the
remaining time is OS/userspace, addressed by the steps above.
