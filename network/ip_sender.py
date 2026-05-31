"""
IP Sender - Registers device IP with central server periodically.
Runs entirely in background thread, never blocks UI.
"""
import socket
import threading
import time
import requests
from ..config import settings


class IPSender:
    """Periodically sends device IP to the central server."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._local_ip = None

    @property
    def local_ip(self):
        if self._local_ip is None:
            self._local_ip = self._get_local_ip()
        return self._local_ip

    def start(self):
        """Start periodic IP registration in background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True, name="IPSender")
        self._thread.start()

    def stop(self):
        """Stop periodic updates."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def send_once(self):
        """Send IP to server once. Returns True on success."""
        ip = self.local_ip
        if not ip:
            return False

        url = f"{settings.SERVER_URL}/id.php?id={settings.DEVICE_ID}&ip={ip}:{settings.FLASK_PORT}"

        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    print(f"✓ Device registered: {ip}:{settings.FLASK_PORT}")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            except requests.exceptions.Timeout:
                pass
            except Exception as e:
                print(f"IP send error: {e}")

            if attempt < 2:
                time.sleep(2 ** attempt)

        print("✗ Device registration failed")
        return False

    def _update_loop(self):
        """Background loop - sends IP every N minutes."""
        # Initial send
        self.send_once()

        while self._running:
            time.sleep(settings.IP_UPDATE_INTERVAL_MINUTES * 60)
            if self._running:
                self._local_ip = None  # Refresh IP
                self.send_once()

    @staticmethod
    def _get_local_ip():
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
