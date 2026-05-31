"""
UART Communication - Alternative to I2C for LED/bulb control.
Uses serial port to send commands to Arduino/MCU.
"""
import threading
from ..config import settings


class UARTBus:
    """UART serial communication for LED control."""

    def __init__(self, port=None, baudrate=None):
        self._serial = None
        self._lock = threading.Lock()
        self._port = port or settings.UART_PORT
        self._baudrate = baudrate or settings.UART_BAUDRATE
        self._init_serial()

    def _init_serial(self):
        """Initialize serial port."""
        try:
            import serial
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=1,
                write_timeout=1
            )
            print(f"UART initialized: {self._port} @ {self._baudrate}")
        except ImportError:
            print("pyserial not installed. Install with: pip3 install pyserial")
            self._serial = None
        except Exception as e:
            print(f"UART init failed ({self._port}): {e}")
            self._serial = None

    @property
    def is_available(self):
        return self._serial is not None and self._serial.is_open

    def write_command(self, cmd):
        """
        Send command string over UART.
        Thread-safe. Appends newline for Arduino Serial.readStringUntil().
        """
        if not self.is_available:
            print(f"UART cmd (no port): {cmd}")
            return False

        with self._lock:
            try:
                data = (cmd + '\n').encode('utf-8')
                self._serial.write(data)
                self._serial.flush()
                return True
            except Exception as e:
                print(f"UART write error: {e}")
                return False

    def read_response(self, timeout=0.5):
        """Read response from device (optional)."""
        if not self.is_available:
            return None

        with self._lock:
            try:
                self._serial.timeout = timeout
                line = self._serial.readline().decode('utf-8').strip()
                return line if line else None
            except Exception as e:
                print(f"UART read error: {e}")
                return None

    def close(self):
        """Close serial port."""
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
