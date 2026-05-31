"""
I2C Bus wrapper - safe initialization and communication.
"""
from ..config import settings


class I2CBus:
    """Thin wrapper around smbus for safe I2C communication."""

    def __init__(self, bus_number=None):
        self._bus = None
        bus_num = bus_number if bus_number is not None else settings.I2C_BUS
        try:
            import smbus
            self._bus = smbus.SMBus(bus_num)
            print(f"I2C bus {bus_num} initialized")
        except ImportError:
            print("I2C: smbus module not available (install python3-smbus)")
        except Exception as e:
            print(f"I2C init failed: {e}")

    @property
    def is_available(self):
        return self._bus is not None

    def write_string(self, address, data_string):
        """Write a string as bytes to I2C device."""
        if not self._bus:
            return False
        try:
            data_bytes = [ord(c) for c in data_string]
            self._bus.write_i2c_block_data(address, data_bytes[0], data_bytes[1:])
            return True
        except Exception as e:
            print(f"I2C write error: {e}")
            return False

    def close(self):
        """Release I2C bus."""
        if self._bus:
            try:
                self._bus.close()
            except:
                pass
            self._bus = None
