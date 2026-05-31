"""
LED Controller - manages all LED states via I2C or UART commands.
Supports both communication methods with automatic fallback.
"""
from ..config import settings
from .i2c import I2CBus
from .uart import UARTBus


class LEDController:
    """Controls medical device LEDs through Arduino via I2C or UART."""

    def __init__(self, i2c_bus=None, uart_bus=None, prefer_uart=True):
        """
        Initialize LED controller.
        Args:
            i2c_bus: I2CBus instance (or None to auto-create)
            uart_bus: UARTBus instance (or None to auto-create)
            prefer_uart: If True, try UART first, fallback to I2C
        """
        self._i2c = i2c_bus or I2CBus()
        self._uart = uart_bus or UARTBus()
        self._prefer_uart = prefer_uart
        self._states = {}       # icon_index -> bool
        self._brightness = {}   # icon_index -> int (0-9)

        # Initialize states from config
        for idx in settings.LED_CONFIGS:
            self._states[idx] = False
            self._brightness[idx] = 5  # Default 50%

        # Report which bus is active
        if self._uart.is_available:
            print("LED Controller: Using UART")
        elif self._i2c.is_available:
            print("LED Controller: Using I2C")
        else:
            print("LED Controller: No communication bus available")

    def toggle(self, icon_index):
        """Toggle LED on/off. Returns new state."""
        new_state = not self._states.get(icon_index, False)
        self.set_state(icon_index, new_state)
        return new_state

    def set_state(self, icon_index, on):
        """Set LED on or off."""
        config = settings.LED_CONFIGS.get(icon_index)
        if not config:
            return False

        self._states[icon_index] = on
        cmd = config['on_cmd'] if on else config['off_cmd']
        return self._send_command(cmd)

    def set_brightness(self, icon_index, level):
        """Set LED brightness (0-9)."""
        level = max(0, min(9, int(level)))
        config = settings.LED_CONFIGS.get(icon_index)
        if not config:
            return False

        self._brightness[icon_index] = level
        cmd = config['brightness_cmd'].format(value=level)
        return self._send_command(cmd)

    def get_state(self, icon_index):
        """Get current LED state."""
        return self._states.get(icon_index, False)

    def get_brightness(self, icon_index):
        """Get current brightness level."""
        return self._brightness.get(icon_index, 5)

    def all_off(self):
        """Turn off all LEDs."""
        for idx in settings.LED_CONFIGS:
            self.set_state(idx, False)

    def _send_command(self, cmd):
        """Send command via preferred bus, fallback to other."""
        if self._prefer_uart:
            if self._uart.is_available:
                return self._uart.write_command(cmd)
            elif self._i2c.is_available:
                return self._i2c.write_string(settings.ARDUINO_ADDRESS, cmd)
        else:
            if self._i2c.is_available:
                return self._i2c.write_string(settings.ARDUINO_ADDRESS, cmd)
            elif self._uart.is_available:
                return self._uart.write_command(cmd)

        print(f"LED cmd (no bus): {cmd}")
        return False

    def close(self):
        """Cleanup all resources."""
        self.all_off()
        self._i2c.close()
        self._uart.close()
