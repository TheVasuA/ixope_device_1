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

        # ─── State ─────────────────────────────────────────────────────────
        self.scope_selected = False
        self.current_scope = None
        self.ui_hidden = False
        self.bulbs_expanded = False
        self._bulb_indices = [5, 6, 7, 8, 11, 12]

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

        # Scope text item (hidden by default)
        self._scope_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, 20, text="", fill="cyan", font=("Arial", 12, "bold")
        )

        # Recording indicator
        self._rec_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, 40, text="", fill="red", font=("Arial", 10, "bold")
        )

        # Temp message text
        self._msg_text = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2,
            text="", fill="white", font=("Arial", 14, "bold")
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
        self._reset_hide_timer()
        self._update_ui()

    # ═══════════════════════════════════════════════════════════════════════
    # RENDER LOOP - Called every frame (~30fps)
    # ═══════════════════════════════════════════════════════════════════════

    def _update_ui(self):
        """Main render loop. Optimized to minimize allocations."""
        self._frame_counter += 1

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
        if self._recorder.is_recording:
            elapsed = self._recorder.elapsed_seconds
            self.canvas.itemconfig(self._rec_text, text=f"● REC {elapsed}s")
        else:
            self.canvas.itemconfig(self._rec_text, text="")

        # Update scope text
        if self.scope_selected and self.current_scope:
            self.canvas.itemconfig(self._scope_text, text=f"SCOPE: {self.current_scope.upper()}")
        else:
            self.canvas.itemconfig(self._scope_text, text="")

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
        for i, item in enumerate(self._icon_items):
            if item is None:
                continue

            # Battery is the system status pip — keep it visible at all times,
            # even when the rest of the UI is auto-hidden. Medical convention.
            if i == 13:
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
                        # Battery shrinks further when the rest is auto-hidden
                        if self.ui_hidden and self._icons.battery_mini_icon is not None:
                            icon = self._icons.battery_mini_icon
                        else:
                            icon = self._icons.get(13)
                        if icon:
                            self.canvas.itemconfig(item, image=icon)
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
        """Draw sliders with tag for efficient removal."""
        if not self._sliders.visible:
            return
        vals = self._sliders.values
        order = ['zoom', 'sharpness', 'exposure', 'brightness', 'contrast']
        labels = {'zoom': 'Zoom', 'sharpness': 'Sharp', 'exposure': 'Exp', 'brightness': 'Bright', 'contrast': 'Contrast'}

        for row, name in enumerate(order):
            y = SLIDER_BASE_Y + row * SLIDER_SPACING
            value = vals[name]

            self.canvas.create_rectangle(SLIDER_START_X, y, SLIDER_START_X + SLIDER_WIDTH, y + 10, fill="#333", outline="#555", tags="slider")
            fw = int(SLIDER_WIDTH * value)
            if fw > 0:
                self.canvas.create_rectangle(SLIDER_START_X, y, SLIDER_START_X + fw, y + 10, fill="#FFF", outline="", tags="slider")
            hx = SLIDER_START_X + int(SLIDER_WIDTH * value)
            self.canvas.create_oval(hx - 8, y - 4, hx + 8, y + 14, fill="white", outline="#333", width=2, tags="slider")
            self.canvas.create_text(SLIDER_START_X - 10, y + 5, text=labels[name], fill="white", font=("Arial", 9, "bold"), anchor="e", tags="slider")

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
        self._show_message("RESTORED", "white", duration=1000)

    # ═══════════════════════════════════════════════════════════════════════
    # SCOPE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def set_scope(self, scope_name):
        """Set current scope (called from scope selection window)."""
        if scope_name in settings.SCOPE_IMAGE_FOLDERS:
            self.current_scope = scope_name
            self.scope_selected = True
            return True
        return False

    def clear_scope(self):
        """Clear scope selection."""
        self.scope_selected = False
        self.current_scope = None

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

    # ═══════════════════════════════════════════════════════════════════════
    # WINDOW LAUNCHERS (lazy imports to save RAM)
    # ═══════════════════════════════════════════════════════════════════════

    def _open_scope_window(self):
        """Open scope selection window."""
        from .windows import ScopeWindow
        if not hasattr(self, '_scope_win') or not self._scope_win.is_open():
            self._scope_win = ScopeWindow(self.root, self)
        else:
            self._scope_win.bring_to_front()

    def _open_led_window(self):
        """Open LED control list window."""
        from .windows import LEDWindow
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
        if not hasattr(self, '_wifi_win') or not self._wifi_win.is_open():
            self._wifi_win = WifiWindow(self.root, self)

    def _open_folder_window(self):
        """Open folder/gallery view."""
        from .windows import FolderWindow
        if not hasattr(self, '_folder_win') or not self._folder_win.is_open():
            self._folder_win = FolderWindow(self.root, self)

    def _open_settings_window(self):
        """Open settings window."""
        from .windows import SettingsWindow
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
