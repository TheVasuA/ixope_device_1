#!/bin/bash
# IXOPE Medical Device - Autostart Script
# Place in: /home/radxa/.config/autostart/ or call from .xinitrc
#
# Boot flow: Power ON → Linux → Auto Login → X11 → This script → UI

# Wait for X11 to be ready
for i in $(seq 1 10); do
	xset q >/dev/null 2>&1 && break
	sleep 0.3
done

# Disable screen blanking and power management
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor
unclutter -idle 0.1 -root &

# Set CPU governor to performance (if available)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null

# Start the application
cd /home/radxa/Documents/tk_ixope
exec python3 -m ixope.app
