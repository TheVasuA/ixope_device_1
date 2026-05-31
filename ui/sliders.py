"""
Slider Manager - handles image adjustment slider state and drag logic.
Drawing is done by main_ui.py directly for performance.
"""
from ..config import settings

# Layout constants (used by main_ui.py for drawing and drag detection)
SLIDER_WIDTH = 300
SLIDER_HEIGHT = 10
SLIDER_START_X = 90
SLIDER_BASE_Y = 100
SLIDER_SPACING = 45


class SliderManager:
    """Manages image adjustment sliders (zoom, sharpness, exposure, brightness, contrast)."""

    def __init__(self):
        self.visible = False
        self.values = {
            'zoom': 0.0,        # 0.0 = 1x, 1.0 = 4x
            'sharpness': 0.0,
            'exposure': 0.5,    # 0.5 = neutral
            'brightness': 0.5,
            'contrast': 0.5,
        }
        self._labels = {
            'zoom': 'Zoom',
            'sharpness': 'Sharp',
            'exposure': 'Exp',
            'brightness': 'Bright',
            'contrast': 'Contrast',
        }
        self._order = ['zoom', 'sharpness', 'exposure', 'brightness', 'contrast']

    def toggle(self):
        """Toggle slider visibility."""
        self.visible = not self.visible
        return self.visible

    def reset_all(self):
        """Reset all values to defaults."""
        self.values['zoom'] = 0.0
        self.values['sharpness'] = 0.0
        self.values['exposure'] = 0.5
        self.values['brightness'] = 0.5
        self.values['contrast'] = 0.5

    def get_zoom_level(self):
        """Convert slider value to zoom multiplier (1.0 - 4.0)."""
        return 1.0 + self.values['zoom'] * 3.0

    def handle_drag(self, x, y):
        """
        Handle drag event. Returns True if a slider was adjusted.
        """
        if not self.visible:
            return False

        for row, name in enumerate(self._order):
            slider_y = SLIDER_BASE_Y + row * SLIDER_SPACING
            if (SLIDER_START_X - 20 <= x <= SLIDER_START_X + SLIDER_WIDTH + 20 and
                    slider_y - 15 <= y <= slider_y + SLIDER_HEIGHT + 15):
                rel = max(0.0, min(1.0, (x - SLIDER_START_X) / SLIDER_WIDTH))
                self.values[name] = rel
                return True

        return False

    def _format_value(self, name, value):
        """Format slider value for display."""
        if name == 'zoom':
            return f"{1.0 + value * 3.0:.1f}x"
        elif name in ('exposure', 'brightness', 'contrast'):
            pct = int(abs(value - 0.5) * 200)
            sign = "+" if value > 0.5 else "-" if value < 0.5 else ""
            return f"{sign}{pct}%"
        else:
            return f"{int(value * 100)}%"
