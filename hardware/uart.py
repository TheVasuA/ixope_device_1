"""
UART Communication - Alternative to I2C for LED/bulb control.
Uses serial port to send commands to Arduino/MCU.

Design: Separate read/write locks so the RX background thread (battery)
never blocks LED write commands. Writes are fast (<1ms for 5 bytes at 9600).
Reads use a short timeout so the RX thread yields frequently.
"""
import threading
from collections import deque
from ..config import settings


class UARTBus:
    """UART serial communication for LED control."""

    def __init__(self, port=None, baudrate=None):
        self._serial = None
        self._write_lock = threading.Lock()
        self._read_lock = threading.Lock()
        self._port = port or settings.UART_PORT
        self._baudrate = baudrate or settings.UART_BAUDRATE
        self._tx_queue = deque(maxlen=32)  # pending write commands
        self._tx_event = threading.Event()
        self._running = True
        self._init_serial()
        # Background TX thread — drains the queue without blocking the UI
        self._tx_thread = threading.Thread(target=self._tx_loop, daemon=True,
                                           name="UART-TX")
        if self.is_available:
            self._tx_thread.start()

    def _init_serial(self):
        """Initialize serial port."""
        try:
            import serial
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=0.1,        # short read timeout — RX thread yields fast
                write_timeout=0.5
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
        Queue a command for async UART send. Returns immediately (non-blocking).
        The TX background thread will send it within milliseconds.
        """
        if not self.is_available:
            return False
        self._tx_queue.append(cmd)
        self._tx_event.set()
        return True

    def write_command_sync(self, cmd):
        """
        Send command synchronously (blocking). Use only when you must
        confirm the write completed before proceeding.
        """
        if not self.is_available:
            return False
        with self._write_lock:
            try:
                data = (cmd + '\n').encode('utf-8')
                self._serial.write(data)
                self._serial.flush()
                return True
            except Exception as e:
                print(f"UART write error: {e}")
                return False

    def _tx_loop(self):
        """Background thread: drain TX queue as fast as possible."""
        while self._running:
            self._tx_event.wait(timeout=0.5)
            self._tx_event.clear()
            while self._tx_queue:
                cmd = self._tx_queue.popleft()
                with self._write_lock:
                    try:
                        data = (cmd + '\n').encode('utf-8')
                        self._serial.write(data)
                        self._serial.flush()
                    except Exception as e:
                        print(f"UART TX error: {e}")

    def read_response(self, timeout=0.1):
        """Read a line from the device. Short timeout to avoid blocking."""
        if not self.is_available:
            return None

        with self._read_lock:
            try:
                self._serial.timeout = timeout
                line = self._serial.readline().decode('utf-8').strip()
                return line if line else None
            except Exception as e:
                print(f"UART read error: {e}")
                return None

    def close(self):
        """Close serial port."""
        self._running = False
        self._tx_event.set()  # wake TX thread so it exits
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
