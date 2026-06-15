"""
Main Medical UI - Ultra-optimized Tkinter fullscreen camera display.

PERFORMANCE OPTIMIZATIONS:
1. Circular mask is pre-computed ONCE and reused every frame
2. PhotoImage is reused (paste into existing) instead of recreating
3. canvas.delete("all") replaced with itemconfig (update existing items)
4. Frame processing avoids unnecessary copies
5. Recording runs in separate thread (never touches UI loop)
6. GC is manually controlled to prevent random pauses
7. Touch events are debounced
8. Icons are drawn once and shown/hidden via canvas item state
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import cv2
import numpy as np
import time
import gc
import threading

from ..config import settings
from ..camera import CameraManager, Recorder
from ..camera.zoom import apply_zoom, apply_brightness, apply_contrast, apply_sharpness, apply_exposure
from ..hardware import LEDController
from ..network import IPSender
from ..storage import FileManager
from .icons import IconManager
from .sliders import SliderManager, SLIDER_WIDTH, SLIDER_HEIGHT, SLIDER_START_X, SLIDER_BASE_Y, SLIDER_SPACING
from .touch_events import hit_test_icon, in_zone, TouchDebouncer, FOCUS_INCREASE_ZONE, FOCUS_DECREASE_ZONE, RESTORE_ZONE
from . import windows as _windows_mod  # access _windows_mod._SF_FONT by reference so late-init is visible


class MedicalUI:
    """
    Main application class - manages the fullscreen medical camera UI.
    Designed for low-RAM ARM SBCs with touchscreen.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("IXOPE Medical")
        self.root.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.root.configure(bg="black")
        self.root.overrideredirect(True)

        # Resolve SF Pro font now that Tk is running
        if not _windows_mod._SF_FONT_RESOLVED:
            _windows_mod._init_sf_font()

        # Re-apply the saved Wi-Fi country regulatory domain on boot
        _windows_mod.apply_saved_country()

        # ─── Disable GC during frame rendering ─────────────────────────────
        gc.disable()
        self._frame_counter = 0

        # ─── Core subsystems ───────────────────────────────────────────────
        self._camera = CameraManager()
        self._recorder = Recorder(self._camera)
        self._leds = LEDController()  # Auto-detects UART or I2C
        self._files = FileManager()
        self._ip_sender = IPSender()
        self._icons = IconManager()
        self._sliders = SliderManager()
        self._touch = TouchDebouncer()

        # ─── Load saved preferences ───────────────────────────────────────
        from ..config.prefs import load as _load_prefs, save as _save_prefs
        self._prefs = _load_prefs()
        self._save_prefs = _save_prefs

        # ─── State ─────────────────────────────────────────────────────────
        # Restore last scope from prefs
        last_scope = self._prefs.get('last_scope')
        if last_scope and last_scope in settings.SCOPE_IMAGE_FOLDERS:
            self.scope_selected = True
            self.current_scope = last_scope
        else:
            self.scope_selected = False
            self.current_scope = None
        self.ui_hidden = False
        self.bulbs_expanded = False
        self._bulb_indices = [5, 6, 7, 8, 11, 12]

        # Restore camera slider values from prefs
        cam = self._prefs.get('camera', {})
        for k in ('zoom', 'brightness', 'contrast', 'exposure', 'sharpness'):
            if k in cam:
                self._sliders.values[k] = cam[k]

        # Restore icon hide delay from prefs
        delay_s = self._prefs.get('icon_hide_delay_s', 7)
        settings.UI_HIDE_DELAY_MS = delay_s * 1000

        # Icon visibility (True = shown)
        self._icon_visible = [
            True,   # 0 camera
            True,   # 1 video
            True,   # 2 scope
            True,   # 3 wifi
            True,   # 4 main_bulb
            False,  # 5 blue_bulb
            False,  # 6 slit_bulb
            False,  # 7 non_polarized
            False,  # 8 polarized
            True,   # 9 folder
            True,   # 10 settings
            False,  # 11 new_non_polarized
            False,  # 12 new_polarized
            True,   # 13 battery
        ]
        self._saved_visibility = None

        # Focus
        self._focus_level = 128
        self._manual_focus = False

        # Auto-hide timer
        self._hide_timer = None

        # Battery on-canvas position (toggled between normal + idle anchors)
        self._battery_pos = settings.ICON_POSITIONS[13]

        # ─── Canvas ────────────────────────────────────────────────────────
        self.canvas = tk.Canvas(
            root, width=settings.WINDOW_WIDTH, height=settings.WINDOW_HEIGHT,
            bg="black", highlightthickness=0
        )
        self.canvas.pack()

        # ─── Pre-compute circular mask (ONCE) ─────────────────────────────
        self._mask = Image.new("L", (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT), 0)
        ImageDraw.Draw(self._mask).ellipse(
            (0, 0, settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT), fill=255
        )

        # ─── Pre-create canvas items (update instead of delete/recreate) ──
        # Main camera image
        self._blank_img = Image.new("RGBA", (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT), (0, 0, 0, 0))
        self._blank_img.putalpha(self._mask)
        self._photo = ImageTk.PhotoImage(self._blank_img)
        self._img_item = self.canvas.create_image(
            settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2, image=self._photo
        )

        # Scope text items — outlined for visibility over any camera content
        # Dark shadow drawn in 4 directions + 4 diagonals, then bright text on top
        scope_y = 20
        scope_font = ("Arial", 14, "bold")
        self._scope_outline_items = []
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            item = self.canvas.create_text(
                settings.WINDOW_WIDTH // 2 + dx, scope_y + dy,
                text="", fill="black", font=scope_font
            )
            self._scope_outline_items.append(item)
        self._scope_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, scope_y, text="", fill="#00ffcc", font=scope_font
        )

        # Recording indicator — placed at the bottom of the screen to avoid
        # merging with the battery/scope indicators at the top
        self._rec_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT - 30,
            text="", fill="red", font=("Arial", 12, "bold")
        )

        # Temp message text
        self._msg_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2,
            text="", fill="white", font=(_windows_mod._SF_FONT, 16, "bold")
        )
        self._msg_timer = None

        # Icon canvas items (created once, visibility toggled)
        self._icon_items = []
        for i, (x, y) in enumerate(settings.ICON_POSITIONS):
            icon_img = self._icons.get(i)
            if icon_img:
                item = self.canvas.create_image(x, y, image=icon_img, state="normal" if self._icon_visible[i] else "hidden")
            else:
                item = None
            self._icon_items.append(item)

        # ─── Bindings ─────────────────────────────────────────────────────
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<Escape>", lambda e: self._shutdown())

        # ─── Start subsystems ─────────────────────────────────────────────
        self._camera.start()
        self._ip_sender.start()

        # Start Flask server (imported lazily to avoid circular deps)
        self._start_flask()

        # ─── Begin render loop ────────────────────────────────────────────
        self._poll_battery()  # show real battery % from the first frame
        self._reset_hide_timer()
        self._update_ui()

    # ═══════════════════════════════════════════════════════════════════════
    # RENDER LOOP - Called every frame (~30fps)
    # ═══════════════════════════════════════════════════════════════════════

    def _update_ui(self):
        """Main render loop. Optimized to minimize allocations."""
        self._frame_counter += 1

        # Poll battery roughly every ~10s (cheap; reads a sysfs file once)
        if self._frame_counter % settings.BATTERY_POLL_FRAMES == 0:
            self._poll_battery()

        # Periodic GC (every ~5 seconds at 30fps)
        if self._frame_counter % settings.GC_INTERVAL_FRAMES == 0:
            gc.collect(generation=0)  # Only youngest generation

        # Get frame (reference, no copy)
        frame = self._camera.get_frame()

        if frame is not None:
            # Apply image adjustments only if sliders are active
            if self._sliders.visible:
                vals = self._sliders.values
                zoom = self._sliders.get_zoom_level()
                if zoom > 1.0:
                    frame = apply_zoom(frame, zoom)
                if vals['brightness'] != 0.5:
                    frame = apply_brightness(frame, vals['brightness'])
                if vals['contrast'] != 0.5:
                    frame = apply_contrast(frame, vals['contrast'])
                if vals['sharpness'] > 0.05:
                    frame = apply_sharpness(frame, vals['sharpness'])
                if vals['exposure'] != 0.5:
                    frame = apply_exposure(frame, vals['exposure'])
            elif self._sliders.get_zoom_level() > 1.0:
                frame = apply_zoom(frame, self._sliders.get_zoom_level())

            # Resize to display dimensions
            if frame.shape[1] != settings.WINDOW_WIDTH or frame.shape[0] != settings.WINDOW_HEIGHT:
                frame = cv2.resize(frame, (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT), interpolation=cv2.INTER_LINEAR)

            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create PIL image and apply mask
            img = Image.fromarray(frame_rgb)
            img.putalpha(self._mask)

        else:
            # No camera - show black with mask
            img = self._blank_img

        # Update the existing PhotoImage (avoids creating new one)
        self._photo.paste(img)

        # Update recording indicator
        if self._recorder.is_recording and not getattr(self, '_window_open', False):
            elapsed = self._recorder.elapsed_seconds
            self.canvas.itemconfig(self._rec_text, text=f"● REC {elapsed}s")
        else:
            self.canvas.itemconfig(self._rec_text, text="")

        # Update scope text — hidden when UI idle or a window is open
        if self.scope_selected and self.current_scope and not self.ui_hidden and not getattr(self, '_window_open', False):
            scope_str = f"SCOPE: {self.current_scope.upper()}"
            self.canvas.itemconfig(self._scope_text, text=scope_str)
            for item in self._scope_outline_items:
                self.canvas.itemconfig(item, text=scope_str)
        else:
            self.canvas.itemconfig(self._scope_text, text="")
            for item in self._scope_outline_items:
                self.canvas.itemconfig(item, text="")

        # Draw sliders (only when visible)
        if self._sliders.visible:
            self.canvas.delete("slider")  # Only delete slider items
            self._draw_sliders()

        # Update icon visibility/state
        self._update_icons()

        # Schedule next frame
        self.root.after(settings.FRAME_INTERVAL_MS, self._update_ui)

    def _update_icons(self):
        """Update icon visibility. Only updates images when state changes."""
        # When a sub-window is open, all icons stay hidden (no blending)
        window_open = getattr(self, '_window_open', False)

        for i, item in enumerate(self._icon_items):
            if item is None:
                continue

            if window_open:
                should_show = False
            elif i == 13:
                # Battery is the system status pip — keep visible even on idle
                should_show = self._icon_visible[i]
            else:
                should_show = self._icon_visible[i] and not self.ui_hidden
            target_state = "normal" if should_show else "hidden"

            try:
                # Only update state if changed
                current_state = self.canvas.itemcget(item, "state")
                if current_state != target_state:
                    self.canvas.itemconfig(item, state=target_state)

                # Only update image for dynamic icons (recording + bulbs + battery)
                if should_show:
                    if i == 13:
                        # On idle (UI hidden), the battery becomes the only
                        # status pip: it grows and moves up to the very top.
                        # When the UI is active it sits at its normal spot/size.
                        if self.ui_hidden:
                            icon = self._icons.get_battery_icon(big=True)
                            target_pos = settings.BATTERY_POS_HIDDEN
                        else:
                            icon = self._icons.get_battery_icon(big=False)
                            target_pos = settings.ICON_POSITIONS[13]
                        if icon:
                            self.canvas.itemconfig(item, image=icon)
                        # Reposition only when it actually changes
                        if self._battery_pos != target_pos:
                            self.canvas.coords(item, target_pos[0], target_pos[1])
                            self._battery_pos = target_pos
                    elif i == 1 and self._recorder.is_recording:
                        rec_icon = self._icons.get_recording_icon()
                        if rec_icon:
                            self.canvas.itemconfig(item, image=rec_icon)
                    elif i == 1 and not self._recorder.is_recording:
                        icon = self._icons.get(1)
                        if icon:
                            self.canvas.itemconfig(item, image=icon)
                    elif i in self._bulb_indices:
                        is_on = self._leds.get_state(i)
                        icon = self._icons.get(i, is_on=is_on)
                        if icon:
                            self.canvas.itemconfig(item, image=icon)
            except tk.TclError:
                icon = self._icons.get(i)
                if icon and should_show:
                    x, y = settings.ICON_POSITIONS[i]
                    self.canvas.delete(item)
                    self._icon_items[i] = self.canvas.create_image(x, y, image=icon, state="normal")

    def _draw_sliders(self):
        """Draw camera color-correction sliders as anti-aliased PIL images
        for high-quality smooth rendering (no jagged Tkinter canvas shapes)."""
        if not self._sliders.visible:
            return
        from PIL import Image, ImageDraw, ImageFilter

        vals = self._sliders.values
        order = ['brightness', 'contrast', 'exposure', 'sharpness']
        labels = {'brightness': 'Brightness', 'contrast': 'Contrast',
                  'exposure': 'Exposure', 'sharpness': 'Sharpness'}

        W = settings.WINDOW_WIDTH
        H = settings.WINDOW_HEIGHT
        cx = W // 2
        slider_w = 260
        start_x = cx - slider_w // 2
        base_y = 140
        spacing = 54

        # Render the entire slider overlay as a single anti-aliased image
        # at 2x resolution then downscale (supersampling AA)
        scale = 2
        img = Image.new("RGBA", (W * scale, H * scale), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # Title
        try:
            from PIL import ImageFont
            title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28)
            label_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
            pct_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 20)
            btn_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
        except Exception:
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
                label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
                pct_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
                btn_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            except Exception:
                title_font = label_font = pct_font = btn_font = None

        # Title text with outline
        title_y = (base_y - 30) * scale
        if title_font:
            bbox = d.textbbox((0, 0), "Camera Settings", font=title_font)
            tw = bbox[2] - bbox[0]
            tx = cx * scale - tw // 2
            ty = title_y - 14
            # Dark outline
            for ox, oy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
                d.text((tx + ox, ty + oy), "Camera Settings",
                       fill=(0, 0, 0, 200), font=title_font)
            d.text((tx, ty), "Camera Settings",
                   fill=(255, 220, 60, 255), font=title_font)

        # Colors — use bright yellow-green for labels (visible on any camera content)
        # with dark outline for contrast
        label_col = (255, 220, 60, 255)      # warm yellow — never lost in the feed
        pct_col = (0, 200, 255, 255)         # cyan for percentages
        accent = (0, 200, 255, 255)
        track_bg = (58, 63, 85, 220)
        white = (255, 255, 255, 255)
        outline_col = (0, 0, 0, 200)         # dark outline for text stroke
        track_h = 10 * scale
        handle_r = 14 * scale

        for row, name in enumerate(order):
            y = (base_y + row * spacing) * scale
            value = vals[name]
            sx = start_x * scale
            sw = slider_w * scale

            # Label with dark outline (drawn 4x offset for stroke effect)
            label_y = y - 44  # more gap above the track
            if label_font:
                for ox, oy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
                    d.text((sx + ox, label_y + oy), labels[name], fill=outline_col, font=label_font)
                d.text((sx, label_y), labels[name], fill=label_col, font=label_font)

                pct_text = f"{int(value * 100)}%"
                bbox = d.textbbox((0, 0), pct_text, font=pct_font)
                pw = bbox[2] - bbox[0]
                for ox, oy in [(-2,0),(2,0),(0,-2),(0,2)]:
                    d.text((sx + sw - pw + ox, label_y + oy), pct_text, fill=outline_col, font=pct_font)
                d.text((sx + sw - pw, label_y), pct_text, fill=pct_col, font=pct_font)

            # Track background (rounded pill)
            tr_y = y
            d.rounded_rectangle([sx, tr_y - track_h//2, sx + sw, tr_y + track_h//2],
                               radius=track_h//2, fill=track_bg)

            # Filled portion
            fw = int(sw * value)
            if fw > track_h:
                d.rounded_rectangle([sx, tr_y - track_h//2, sx + fw, tr_y + track_h//2],
                                   radius=track_h//2, fill=accent)

            # Handle shadow
            hx = sx + int(sw * value)
            d.ellipse([hx - handle_r + 2, tr_y - handle_r + 3,
                      hx + handle_r + 2, tr_y + handle_r + 3],
                     fill=(10, 10, 20, 120))
            # Handle body
            d.ellipse([hx - handle_r, tr_y - handle_r,
                      hx + handle_r, tr_y + handle_r],
                     fill=white, outline=accent, width=5)
            # Handle inner dot
            dot_r = 6
            d.ellipse([hx - dot_r, tr_y - dot_r, hx + dot_r, tr_y + dot_r],
                     fill=accent)

        # ─── Buttons ─────────────────────────────────────────────────
        btn_y = (base_y + len(order) * spacing + 20) * scale
        btn_w = 110 * scale
        btn_h = 34 * scale
        gap = 12 * scale
        btn_r = btn_h // 2

        # DEFAULTS (left)
        dx = cx * scale - gap // 2 - btn_w // 2
        d.rounded_rectangle([dx - btn_w//2, btn_y - btn_h//2,
                            dx + btn_w//2, btn_y + btn_h//2],
                           radius=btn_r, fill=track_bg, outline=(90, 96, 122, 255), width=3)
        if btn_font:
            bbox = d.textbbox((0, 0), "DEFAULTS", font=btn_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            d.text((dx - tw//2, btn_y - th//2 - bbox[1]), "DEFAULTS", fill=white, font=btn_font)

        # SAVE (right)
        sx_btn = cx * scale + gap // 2 + btn_w // 2
        d.rounded_rectangle([sx_btn - btn_w//2, btn_y - btn_h//2,
                            sx_btn + btn_w//2, btn_y + btn_h//2],
                           radius=btn_r, fill=accent)
        if btn_font:
            bbox = d.textbbox((0, 0), "SAVE", font=btn_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            d.text((sx_btn - tw//2, btn_y - th//2 - bbox[1]), "SAVE",
                   fill=(10, 10, 20, 255), font=btn_font)

        # Downscale 2x → 1x with LANCZOS (smooth AA)
        img = img.resize((W, H), Image.LANCZOS)
        self._slider_photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(cx, H // 2, image=self._slider_photo, tags="slider")

        # Store button hit zones (at 1x coordinates)
        btn_y_1x = base_y + len(order) * spacing + 20
        dx_1x = cx - (12 // 2 + 110 // 2)
        sx_1x = cx + (12 // 2 + 110 // 2)
        self._slider_defaults_z = (dx_1x - 55, btn_y_1x - 17, dx_1x + 55, btn_y_1x + 17)
        self._slider_save_z = (sx_1x - 55, btn_y_1x - 17, sx_1x + 55, btn_y_1x + 17)

    def _poll_battery(self):
        """Read the system battery level and update the icon if it changed.

        Reads Linux sysfs (`/sys/class/power_supply/*/capacity`) which the
        Radxa exposes when a fuel gauge / charger driver is present. On
        machines without a battery this simply does nothing and the icon
        keeps its last known value.
        """
        level = self._read_battery_capacity()
        if level is not None and self._icons.set_battery_level(level):
            # Force the on-canvas battery image to refresh next frame
            item = self._icon_items[13] if len(self._icon_items) > 13 else None
            if item is not None:
                try:
                    icon = self._icons.get_battery_icon(big=self.ui_hidden)
                    if icon:
                        self.canvas.itemconfig(item, image=icon)
                except tk.TclError:
                    pass

    @staticmethod
    def _read_battery_capacity():
        """Return battery % (0-100) from sysfs, or None if unavailable."""
        import glob
        try:
            for base in glob.glob("/sys/class/power_supply/*"):
                cap_path = f"{base}/capacity"
                type_path = f"{base}/type"
                try:
                    with open(type_path) as f:
                        if f.read().strip().lower() != "battery":
                            continue
                except OSError:
                    pass
                try:
                    with open(cap_path) as f:
                        return int(f.read().strip())
                except (OSError, ValueError):
                    continue
        except Exception:
            pass
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # TOUCH / CLICK HANDLING
    # ═══════════════════════════════════════════════════════════════════════

    def _on_click(self, event):
        """Handle touch/click with debouncing."""
        if not self._touch.should_process():
            return

        x, y = event.x, event.y

        # If UI is hidden, restore it
        if self.ui_hidden:
            self._restore_ui()
            return

        # Check slider drag first
        if self._sliders.visible and self._sliders.handle_drag(x, y):
            self._reset_hide_timer()
            return

        # Check DEFAULTS / SAVE buttons when sliders are visible
        if self._sliders.visible:
            if hasattr(self, '_slider_defaults_z'):
                x1, y1, x2, y2 = self._slider_defaults_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    # Reset all to neutral (0.5 for brightness/contrast/exposure, 0 for sharpness)
                    self._sliders.values['brightness'] = 0.5
                    self._sliders.values['contrast'] = 0.5
                    self._sliders.values['exposure'] = 0.5
                    self._sliders.values['sharpness'] = 0.0
                    self._show_message("DEFAULTS", "white", duration=800)
                    return
            if hasattr(self, '_slider_save_z'):
                x1, y1, x2, y2 = self._slider_save_z
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self._save_camera_prefs()
                    self._toggle_sliders()  # close sliders after save
                    self._show_message("SAVED ✓", "green", duration=1000)
                    return

        # Check focus zones (invisible)
        if in_zone(x, y, FOCUS_INCREASE_ZONE):
            self._adjust_focus(+10)
            return
        if in_zone(x, y, FOCUS_DECREASE_ZONE):
            self._adjust_focus(-10)
            return
        if in_zone(x, y, RESTORE_ZONE):
            self._restore_defaults()
            return

        # Hit-test icons
        hit = hit_test_icon(x, y, settings.ICON_POSITIONS, self._icon_visible)
        if hit >= 0:
            self._handle_icon_tap(hit)
            self._reset_hide_timer()
            return

        self._reset_hide_timer()

    def _on_drag(self, event):
        """Handle drag for sliders."""
        if self._sliders.visible:
            self._sliders.handle_drag(event.x, event.y)

    def _handle_icon_tap(self, index):
        """Process icon tap by index. Shows press feedback (cyan glow + magnification)."""
        # Visual press feedback
        self._show_press_feedback(index)

        if index == 0:  # Camera - capture image
            self._capture_image()

        elif index == 1:  # Video - start/stop recording
            self._toggle_recording()

        elif index == 2:  # Scope selection
            self._open_scope_window()

        elif index == 3:  # WiFi
            self._open_wifi_window()

        elif index == 4:  # Main bulb - open LED control window
            self._open_led_window()

        elif index in self._bulb_indices:  # LED toggle (direct)
            self._leds.toggle(index)

        elif index == 9:  # Folder
            self._open_folder_window()

        elif index == 10:  # Settings
            self._open_settings_window()

        elif index == 13:  # Battery - ignore
            pass

    def _show_press_feedback(self, index):
        """
        Liquid touch feedback at the icon's exact position (no offset, no
        hard ring around the icon):
          • Pre-rendered cyan ripple frames radiate from the icon center
          • Icon swaps to its 'pressed' (magnified, brighter) variant
          • Both layers are anchored to ICON_POSITIONS[index] so what the
            user sees == where they tapped
        """
        if index < 0 or index >= len(self._icon_items):
            return
        item = self._icon_items[index]
        if item is None:
            return

        x, y = settings.ICON_POSITIONS[index]

        # Cancel any in-flight feedback for this icon
        timer_attr = f"_press_timer_{index}"
        if hasattr(self, timer_attr):
            try:
                self.root.after_cancel(getattr(self, timer_attr))
            except Exception:
                pass

        ripple_attr = f"_ripple_after_{index}"
        if hasattr(self, ripple_attr):
            try:
                self.root.after_cancel(getattr(self, ripple_attr))
            except Exception:
                pass

        # ─── Liquid ripple: animated pre-rendered cyan caustic ────────
        ripple_frame_count = self._icons.ripple_frame_count()
        if ripple_frame_count > 0:
            ripple_tag = f"ripple_{index}"
            self.canvas.delete(ripple_tag)
            first = self._icons.get_ripple_frame(0)
            if first is not None:
                ripple_item = self.canvas.create_image(
                    x, y, image=first, tags=ripple_tag
                )
                # Ripple draws BELOW the icon so the icon stays readable
                try:
                    self.canvas.tag_lower(ripple_item, item)
                except tk.TclError:
                    pass

                def _step(i=0):
                    if i >= ripple_frame_count:
                        self.canvas.delete(ripple_tag)
                        return
                    img = self._icons.get_ripple_frame(i)
                    try:
                        if img is not None:
                            self.canvas.itemconfig(ripple_item, image=img)
                    except tk.TclError:
                        return
                    nxt = self.root.after(28, lambda: _step(i + 1))
                    setattr(self, ripple_attr, nxt)

                _step(0)

        # ─── Magnify: swap to pressed (larger, brighter) variant ─────
        pressed_icon = self._icons.get(index, pressed=True)
        if pressed_icon is not None:
            try:
                self.canvas.itemconfig(item, image=pressed_icon)
                self.canvas.tag_raise(item)
            except tk.TclError:
                pass

        # ─── Restore default icon after the press window ─────────────
        def restore():
            if index < 0 or index >= len(self._icon_items):
                return
            it = self._icon_items[index]
            if it is None:
                return
            try:
                if index in self._bulb_indices:
                    is_on = self._leds.get_state(index)
                    icon = self._icons.get(index, is_on=is_on)
                elif index == 1 and self._recorder.is_recording:
                    icon = self._icons.get_recording_icon()
                else:
                    icon = self._icons.get(index)
                if icon is not None:
                    self.canvas.itemconfig(it, image=icon)
            except tk.TclError:
                pass

        timer = self.root.after(220, restore)
        setattr(self, timer_attr, timer)

    def _restore_icon(self, index):
        """Restore icon to default state (kept for compatibility)."""
        if index < 0 or index >= len(self._icon_items):
            return
        item = self._icon_items[index]
        if item is None:
            return
        try:
            if index in self._bulb_indices:
                is_on = self._leds.get_state(index)
                icon = self._icons.get(index, is_on=is_on)
            elif index == 1 and self._recorder.is_recording:
                icon = self._icons.get_recording_icon()
            else:
                icon = self._icons.get(index)
            if icon:
                self.canvas.itemconfig(item, image=icon)
        except tk.TclError:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _capture_image(self):
        """Capture current frame and save/upload in background."""
        if not self.scope_selected:
            self._show_message("SELECT SCOPE FIRST", "white")
            return

        # Check disk space
        ok, free = self._files.check_disk_space()
        if not ok:
            self._show_message(f"DISK FULL ({free:.0f}MB)", "red")
            return

        frame = self._camera.get_frame_copy()  # BGR format from camera
        if frame is None:
            self._show_message("NO FRAME", "red")
            return

        self._show_message("CAPTURING...", "yellow", duration=800)

        def on_saved(success, path):
            if success:
                self.root.after(0, lambda: self._show_message("CAPTURED ✓", "green"))
            else:
                self.root.after(0, lambda: self._show_message("SAVE FAILED", "red"))

        self._files.save_image(frame, self.current_scope, callback=on_saved)

    def _toggle_recording(self):
        """Start or stop video recording."""
        if not self.scope_selected:
            self._show_message("SELECT SCOPE FIRST", "white")
            return

        if not self._camera.is_available:
            self._show_message("NO CAMERA", "red")
            return

        if not self._recorder.is_recording:
            success = self._recorder.start(self.current_scope)
            if success:
                self._show_message("● RECORDING", "red", duration=1500)
                # Auto-stop after max duration
                self.root.after(
                    settings.MAX_RECORD_SECONDS * 1000,
                    self._auto_stop_recording
                )
            else:
                self._show_message("RECORD FAILED", "red")
        else:
            path = self._recorder.stop()
            self._show_message("SAVED ✓", "green")
            if path:
                self._files.upload_video(path, self.current_scope)

    def _auto_stop_recording(self):
        """Auto-stop recording after max duration."""
        if self._recorder.is_recording:
            path = self._recorder.stop()
            self._show_message("REC COMPLETE", "green")
            if path:
                self._files.upload_video(path, self.current_scope)

    def _adjust_focus(self, delta):
        """Adjust camera focus."""
        self._focus_level = max(0, min(255, self._focus_level + delta))
        self._camera.set_focus(self._focus_level)
        self._show_message(f"FOCUS: {self._focus_level}", "cyan", duration=500)

    def _restore_defaults(self):
        """Reset all image settings."""
        self._sliders.reset_all()
        self._focus_level = 128
        self._camera.set_autofocus(True)
        self._save_camera_prefs()
        self._show_message("RESTORED", "white", duration=1000)

    def _save_camera_prefs(self):
        """Persist current slider values to prefs."""
        self._prefs['camera'] = dict(self._sliders.values)
        self._save_prefs(self._prefs)

    # ═══════════════════════════════════════════════════════════════════════
    # SCOPE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def set_scope(self, scope_name):
        """Set current scope (called from scope selection window)."""
        if scope_name in settings.SCOPE_IMAGE_FOLDERS:
            self.current_scope = scope_name
            self.scope_selected = True
            # Persist the selection
            self._prefs['last_scope'] = scope_name
            self._save_prefs(self._prefs)
            return True
        return False

    def clear_scope(self):
        """Clear scope selection."""
        self.scope_selected = False
        self.current_scope = None
        self._prefs['last_scope'] = None
        self._save_prefs(self._prefs)

    # ═══════════════════════════════════════════════════════════════════════
    # UI HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def _show_message(self, text, color="white", duration=2000):
        """Show temporary message on screen."""
        self.canvas.itemconfig(self._msg_text, text=text, fill=color)
        if self._msg_timer:
            self.root.after_cancel(self._msg_timer)
        self._msg_timer = self.root.after(duration, lambda: self.canvas.itemconfig(self._msg_text, text=""))

    def _reset_hide_timer(self):
        """Reset the auto-hide timer for UI elements."""
        if self._hide_timer:
            self.root.after_cancel(self._hide_timer)
        self._hide_timer = self.root.after(settings.UI_HIDE_DELAY_MS, self._hide_ui)

    def _hide_ui(self):
        """Hide UI icons after inactivity."""
        self.ui_hidden = True

    def _restore_ui(self):
        """Show UI icons again."""
        self.ui_hidden = False
        self._reset_hide_timer()

    def _toggle_sliders(self):
        """Toggle slider mode."""
        showing = self._sliders.toggle()
        if showing:
            self._saved_visibility = self._icon_visible.copy()
            self._icon_visible = [False] * len(self._icon_visible)
            self._icon_visible[13] = True  # Keep battery
        else:
            if self._saved_visibility:
                self._icon_visible = self._saved_visibility
            self.canvas.delete("slider")
            # Persist slider positions when the user closes sliders
            self._save_camera_prefs()

    # ═══════════════════════════════════════════════════════════════════════
    # WINDOW LAUNCHERS (lazy imports to save RAM)
    # ═══════════════════════════════════════════════════════════════════════

    def _hide_all_icons(self):
        """Immediately hide all icons + scope/rec text so they don't blend
        with an overlay window that's about to open."""
        self._window_open = True

    def _show_all_icons(self):
        """Restore icon visibility (called when a window closes)."""
        self._window_open = False
        self._reset_hide_timer()

    def _open_scope_window(self):
        """Open scope selection window."""
        from .windows import ScopeWindow
        self._hide_all_icons()
        if not hasattr(self, '_scope_win') or not self._scope_win.is_open():
            self._scope_win = ScopeWindow(self.root, self)
        else:
            self._scope_win.bring_to_front()

    def _open_led_window(self):
        """Open LED control list window."""
        from .windows import LEDWindow
        self._hide_all_icons()
        if not hasattr(self, '_led_win') or not self._led_win.is_open():
            self._led_win = LEDWindow(self.root, self)
        else:
            self._led_win.bring_to_front()

    def refresh_icons(self):
        """Force refresh all icon images on canvas (after scheme change)."""
        for i, item in enumerate(self._icon_items):
            if item is None:
                continue
            icon = self._icons.get(i)
            if icon:
                try:
                    self.canvas.itemconfig(item, image=icon)
                except tk.TclError:
                    x, y = settings.ICON_POSITIONS[i]
                    self.canvas.delete(item)
                    self._icon_items[i] = self.canvas.create_image(x, y, image=icon)

    def _open_wifi_window(self):
        """Open WiFi settings window."""
        from .windows import WifiWindow
        self._hide_all_icons()
        if not hasattr(self, '_wifi_win') or not self._wifi_win.is_open():
            self._wifi_win = WifiWindow(self.root, self)

    def _open_folder_window(self):
        """Open folder/gallery view."""
        from .windows import FolderWindow
        self._hide_all_icons()
        if not hasattr(self, '_folder_win') or not self._folder_win.is_open():
            self._folder_win = FolderWindow(self.root, self)

    def _open_settings_window(self):
        """Open settings window."""
        from .windows import SettingsWindow
        self._hide_all_icons()
        if not hasattr(self, '_settings_win') or not self._settings_win.is_open():
            self._settings_win = SettingsWindow(self.root, self)

    # ═══════════════════════════════════════════════════════════════════════
    # FLASK SERVER
    # ═══════════════════════════════════════════════════════════════════════

    def _start_flask(self):
        """Start Flask server in background thread."""
        from ..flask_server.server import start_server
        threading.Thread(target=start_server, args=(self._camera,), daemon=True, name="FlaskServer").start()

    # ═══════════════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ═══════════════════════════════════════════════════════════════════════

    def _shutdown(self):
        """Clean shutdown."""
        self._leds.all_off()
        if self._recorder.is_recording:
            self._recorder.stop()
        self._camera.stop()
        self._ip_sender.stop()
        self._leds.close()
        gc.enable()
        self.root.destroy()
