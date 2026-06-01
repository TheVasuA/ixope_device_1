"""
Global settings and constants for the IXOPE Medical Device.
All tunable parameters in one place.
"""
import os
import math

# ─── Device ───────────────────────────────────────────────────────────────────
DEVICE_ID = "1001"
SERVER_URL = "https://ixope-hub.com"

# ─── Display (480x480 Round Display) ─────────────────────────────────────────
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 480
DISPLAY_RADIUS = 240  # Circular display radius
TARGET_FPS = 30
FRAME_INTERVAL_MS = 33  # 1000 / 30

# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_BUFFER_SIZE = 1
CAMERA_MAX_INDEX = 5
FRAME_QUEUE_SIZE = 2  # Keep only latest frames, drop old ones

# ─── Recording ────────────────────────────────────────────────────────────────
MAX_RECORD_SECONDS = 10
VIDEO_CODECS = ['mp4v', 'avc1', 'X264', 'MJPG', 'XVID']
VIDEO_FPS = 30

# ─── Paths ────────────────────────────────────────────────────────────────────
# BASE_PATH is the root for captured images, videos, logs, and config files.
# Resolution order:
#   1. IXOPE_BASE_PATH env var (lets you point at any folder for testing)
#   2. /home/radxa/Documents/ixope  — production target on the Radxa SBC
#   3. ~/ixope-data                    — fallback on any other machine
#                                        (Windows / Linux dev box / macOS)
def _resolve_base_path():
    env = os.environ.get("IXOPE_BASE_PATH")
    if env:
        return env
    radxa = "/home/radxa/Documents/ixope"
    if os.path.isdir("/home/radxa"):
        return radxa
    return os.path.join(os.path.expanduser("~"), "ixope-data")


BASE_PATH = _resolve_base_path()
ICON_PATH = os.path.join(BASE_PATH)
IMAGE_BASE = os.path.join(BASE_PATH, "captured_images")
VIDEO_BASE = os.path.join(BASE_PATH, "recorded_videos")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_PATH = os.path.join(REPO_ROOT, "deploy")
BOOT_SPLASH_GIF = os.path.join(DEPLOY_PATH, "boot_logo.gif")

SCOPE_IMAGE_FOLDERS = {
    'opth': os.path.join(IMAGE_BASE, "opth"),
    'otto': os.path.join(IMAGE_BASE, "oto"),
    'derm': os.path.join(IMAGE_BASE, "derm"),
    'micro': os.path.join(IMAGE_BASE, "micro"),
}

SCOPE_VIDEO_FOLDERS = {
    'opth': os.path.join(VIDEO_BASE, "opth"),
    'otto': os.path.join(VIDEO_BASE, "oto"),
    'derm': os.path.join(VIDEO_BASE, "derm"),
    'micro': os.path.join(VIDEO_BASE, "micro"),
}

# ─── I2C / Hardware ──────────────────────────────────────────────────────────
I2C_BUS = 11
ARDUINO_ADDRESS = 0x08

# ─── UART (alternative to I2C for LED control) ───────────────────────────────
UART_PORT = "/dev/ttyS0"
UART_BAUDRATE = 9600

# ─── LED Configurations ──────────────────────────────────────────────────────
LED_CONFIGS = {
    5: {'name': 'BLUE LED', 'on_cmd': '*11', 'off_cmd': '*10', 'brightness_cmd': '*1{value}'},
    6: {'name': 'MAIN LED', 'on_cmd': '*41', 'off_cmd': '*40', 'brightness_cmd': '*4{value}'},
    7: {'name': 'NON-POLARIZED LED', 'on_cmd': '*21', 'off_cmd': '*20', 'brightness_cmd': '*2{value}'},
    8: {'name': 'POLARIZED LED', 'on_cmd': '*31', 'off_cmd': '*30', 'brightness_cmd': '*3{value}'},
    11: {'name': 'NEW NON-POLARIZED LED', 'on_cmd': '*21', 'off_cmd': '*20', 'brightness_cmd': '*2{value}'},
    12: {'name': 'NEW POLARIZED LED', 'on_cmd': '*31', 'off_cmd': '*30', 'brightness_cmd': '*3{value}'},
}

# ─── Flask ────────────────────────────────────────────────────────────────────
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
STREAM_JPEG_QUALITY = 70  # Lower = faster streaming, less RAM

# ─── Network ─────────────────────────────────────────────────────────────────
IP_UPDATE_INTERVAL_MINUTES = 10
UPDATE_CHECK_INTERVAL_MINUTES = 60
GIT_REMOTE = "origin"
GIT_BRANCH = "main"
ROLLBACK_ON_FAILURE = True
AUTO_RESTART_ON_UPDATE = True
SYSTEMD_SERVICE_NAME = "ixope"

# ─── UI Icon Positions (480x480 round display) ───────────────────────────────
# Layout philosophy:
#   • 8 evenly-spaced positions on a single outer ring (45° apart)
#     at radius r=170 from the screen center (240, 240). With ICON_SIZE=56
#     each icon's outer edge sits at r=198, giving ~42px from the screen
#     bezel — generous padding so capacitive touch is rock-solid even at
#     the curved edge.
#   • Battery is rendered SMALLER (BATTERY_ICON_SIZE) and pinned at the
#     top status position. It is always shown.
#   • Bulbs (5,6,7,8,11,12) only appear inside the LED Toplevel window so
#     their on-canvas coordinates are purely fallback values — kept on an
#     inner ring r=100 for parity with the rest of the layout.
ICON_SIZE = 56                # primary icons
BATTERY_ICON_SIZE = 22        # battery status pip — small, top of screen
BATTERY_ICON_SIZE_HIDDEN = 16 # even smaller when other icons are auto-hidden

_R_OUTER = 175                # outer ring (primary controls) — closer to bezel
_R_INNER = 100                # inner ring (LED bulbs in the LED window)
_CX, _CY = 240, 240


def _polar(r, deg_from_top):
    """Convert (radius, angle from screen-top, clockwise) to (x, y)."""
    rad = math.radians(deg_from_top - 90)  # -90 makes 0° point straight up
    return (int(_CX + r * math.cos(rad)), int(_CY + r * math.sin(rad)))


# ─── Outer ring at 45° spacing — clock-position layout ─────────────────────
#   12 o'clock (0°)   → battery (small, status)
#    1:30 (45°)       → settings
#    3:00 (90°)       → wifi
#    4:30 (135°)      → video
#    6:00 (180°)      → main_bulb
#    7:30 (225°)      → camera
#    9:00 (270°)      → scope
#   10:30 (315°)      → folder
ICON_POSITIONS = [
    _polar(_R_OUTER, 225),     # 0  camera           (7:30)
    _polar(_R_OUTER, 135),     # 1  video            (4:30)
    _polar(_R_OUTER, 270),     # 2  scope            (9:00)
    _polar(_R_OUTER,  90),     # 3  wifi             (3:00)
    _polar(_R_OUTER, 180),     # 4  main_bulb        (6:00)
    _polar(_R_INNER, 150),     # 5  blue_bulb        (LED window)
    _polar(_R_INNER, 210),     # 6  slit_bulb        (LED window)
    _polar(_R_INNER, 240),     # 7  non_polarized    (LED window)
    _polar(_R_INNER, 270),     # 8  polarized        (LED window)
    _polar(_R_OUTER, 315),     # 9  folder           (10:30)
    _polar(_R_OUTER,  45),     # 10 settings         (1:30)
    _polar(_R_INNER,  90),     # 11 new_non_polarized (LED window)
    _polar(_R_INNER, 120),     # 12 new_polarized    (LED window)
    _polar(_R_OUTER,   0),     # 13 battery          (12:00, rendered small)
]

# Battery sits even higher than the ring so it reads as the system status pip
# (not part of the control cluster). Override the polar position with a fixed
# top-of-screen anchor.
ICON_POSITIONS[13] = (_CX, 26)

# ─── Theme ────────────────────────────────────────────────────────────────────
THEME_DARK = {
    'bg': '#000000',
    'card_bg': '#1a1a2e',
    'card_border': '#2a2a4a',
    'text': '#ffffff',
    'text_secondary': '#8888aa',
    'accent': '#00c8ff',
    'success': '#34c759',
    'danger': '#ff3b30',
    'warning': '#ff9500',
}

THEME_LIGHT = {
    'bg': '#f0f0f5',
    'card_bg': '#ffffff',
    'card_border': '#e0e0e8',
    'text': '#1a1a2e',
    'text_secondary': '#666688',
    'accent': '#007aff',
    'success': '#34c759',
    'danger': '#ff3b30',
    'warning': '#ff9500',
}

# ─── Performance Tuning ──────────────────────────────────────────────────────
GC_INTERVAL_FRAMES = 150  # Run gc.collect() every N frames
UI_HIDE_DELAY_MS = 20000  # Icons visible for 20 seconds before auto-hide
TOUCH_DEBOUNCE_MS = 200  # Minimum ms between touch events
