"""
Touch Event Handler - debounced, efficient touch/click processing.

Key optimizations:
- Debounce prevents multiple rapid touches from queuing
- Hit-test uses simple radius check (no complex geometry)
- Single pass through icon positions

Touch geometry:
- HIT_RADIUS exactly matches the icon's visible radius (+ a small forgiveness
  pad) so the user feels they tapped the icon they see, not a hidden offset.
- Coordinates are screen pixel coordinates on a 1:1 480x480 panel where the
  capacitive touch reports the same coordinate space (no scaling, no offset).
- Scale factor (Tk's `tk scaling`) is forced to 1.0 in app.py so 1 device pixel
  == 1 logical pixel.
"""
import time
from ..config import settings


# Visible icon radius is ICON_SIZE/2. Add 4px forgiveness for fingertip
# pressure and DPI rounding — nothing more, so we stay near the *actual* icon
# instead of grabbing taps meant for the next icon.
HIT_RADIUS = (settings.ICON_SIZE // 2) + 4

# Invisible focus control zones — kept off the icon ring so they don't conflict
# with the polar layout in settings.ICON_POSITIONS (radius 110 / 160).
# Zones live in the dead corners of the inscribed square (top edges), which
# remain inside the visible round display.
FOCUS_INCREASE_ZONE = (140, 200, 200, 320)   # left dead band
FOCUS_DECREASE_ZONE = (280, 200, 340, 320)   # right dead band
RESTORE_ZONE        = (210, 220, 270, 320)   # center dead band


def hit_test_icon(x, y, icon_positions, icon_visible):
    """
    Check which icon was tapped. Returns icon index or -1.
    Uses squared distance to avoid sqrt.
    """
    r_sq = HIT_RADIUS * HIT_RADIUS

    for i, (ix, iy) in enumerate(icon_positions):
        if not icon_visible[i]:
            continue
        dx = x - ix
        dy = y - iy
        if dx * dx + dy * dy <= r_sq:
            return i

    return -1


def in_zone(x, y, zone):
    """Check if point is within a rectangular zone (x1, y1, x2, y2)."""
    return zone[0] <= x <= zone[2] and zone[1] <= y <= zone[3]


class TouchDebouncer:
    """Prevents rapid-fire touch events from overwhelming the UI."""

    def __init__(self, min_interval_ms=None):
        self._min_interval = (min_interval_ms or settings.TOUCH_DEBOUNCE_MS) / 1000.0
        self._last_time = 0

    def should_process(self):
        """Returns True if enough time has passed since last touch."""
        now = time.time()
        if now - self._last_time >= self._min_interval:
            self._last_time = now
            return True
        return False
