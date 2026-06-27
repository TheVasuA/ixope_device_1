"""
LED Controller - manages 6 LEDs with brightness (0-9) via UART.
Also receives battery percentage from MCU and controls liquid lens focus.

Protocol (Radxa → MCU):
  LED:   *XY#   X=LED(1-6), Y=brightness(0=off, 1-9 = 10%-90%)
  All off: OF
  Focus: L24 to L70 (liquid lens, maps 0-100%)

Protocol (MCU → Radxa):
  Battery: B5%, B25%, B77%, B100%
"""
import threading
import re
from ..config import settings
from .uart import UARTBus


class LEDController:
    """Controls medical device LEDs via UART with brightness sliders."""

    def __init__(self):
        self._uart = UARTBus()
        self._lock = threading.Lock()

        # LED states: index (1-6) → brightness level (0-9)
        # 0 = off, 1 = 10%, ... 9 = 90%
        self._brightness = {}
        for idx in settings.LED_CONFIGS:
            self._brightness[idx] = 0  # all off initially

        # Battery level received from MCU
        self._battery_level = None

        # Focus level (0-100 mapped to L24-L70)
        self._focus = 50  # default mid

        # Start UART receive thread for battery updates
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True,
                                           name="UART-RX")
        if self._uart.is_available:
            self._rx_thread.start()
            print("LED Controller: UART active, listening for battery")
        else:
            print("LED Controller: No UART available")

    # ─── LED Control ──────────────────────────────────────────────────────

    def set_brightness(self, led_index, level):
        """Set LED brightness. level: 0 (off) to 9 (90%)."""
        if led_index not in settings.LED_CONFIGS:
            return False
        level = max(0, min(9, int(level)))
        self._brightness[led_index] = level
        config = settings.LED_CONFIGS[led_index]
        cmd = config['brightness_cmd'].format(value=level)
        return self._send(cmd)

    def get_brightness(self, led_index):
        """Get current brightness level (0-9)."""
        return self._brightness.get(led_index, 0)

    def is_on(self, led_index):
        """Check if LED is on (brightness > 0)."""
        return self._brightness.get(led_index, 0) > 0

    def get_state(self, led_index):
        """Compat: returns True if on."""
        return self.is_on(led_index)

    def toggle(self, led_index):
        """Toggle LED on (last brightness or 50%) / off."""
        if self.is_on(led_index):
            self.set_brightness(led_index, 0)
        else:
            self.set_brightness(led_index, 5)  # default 50%

    def all_off(self):
        """Turn off all LEDs with the OF command."""
        for idx in settings.LED_CONFIGS:
            self._brightness[idx] = 0
        self._send(settings.LED_ALL_OFF_CMD)

    # ─── Focus Control ────────────────────────────────────────────────────

    def set_focus(self, percent):
        """Set liquid lens focus. percent: 0-100 → L24-L70."""
        percent = max(0, min(100, int(percent)))
        self._focus = percent
        # Map 0-100% to L24-L70
        value = settings.FOCUS_MIN + int((settings.FOCUS_MAX - settings.FOCUS_MIN) * percent / 100)
        cmd = f"{settings.FOCUS_CMD_PREFIX}{value}"
        return self._send(cmd)

    def get_focus(self):
        """Get current focus percentage."""
        return self._focus

    # ─── Battery (received from MCU) ─────────────────────────────────────

    def get_battery(self):
        """Get last received battery percentage (0-100) or None."""
        return self._battery_level

    def _rx_loop(self):
        """Background thread: read UART for battery updates from MCU."""
        while self._running:
            try:
                line = self._uart.read_response(timeout=0.1)
                if line:
                    self._parse_rx(line)
            except Exception:
                pass

    def _parse_rx(self, line):
        """Parse incoming MCU data. Expected: B5%, B25%, B77%, B100%"""
        line = line.strip()
        # Battery: B followed by number and %
        m = re.match(r'^B(\d+)%?$', line)
        if m:
            self._battery_level = max(0, min(100, int(m.group(1))))

    # ─── Internal ─────────────────────────────────────────────────────────

    def _send(self, cmd):
        """Send command via UART."""
        if self._uart.is_available:
            print(f"{cmd}")
            return self._uart.write_command(cmd)
        return False

    def close(self):
        """Cleanup."""
        self._running = False
        self.all_off()
        self._uart.close()
