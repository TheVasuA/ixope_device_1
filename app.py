#!/usr/bin/env python3
"""
IXOPE Medical Device - Main Entry Point

Boot flow:
  Power ON → Linux Boot → Auto Login → X11 → This script → Fullscreen UI

Usage:
  python3 -m ixope.app
"""
import sys
import os
import gc
import logging
import threading
import tkinter as tk
from typing import Any
from logging.handlers import RotatingFileHandler

# ─── Allow running this file directly (e.g. Thonny "Run", `python app.py`) ──
# app.py lives inside a package and uses relative imports (`from .config ...`).
# Those only resolve when the file is loaded as part of a package. When it is
# executed as a plain script there is no package context, so we re-launch it
# as a proper module under its actual package (= its folder name, which may be
# "ixope", "tk_ixope", etc.). This makes the app runnable regardless of how it
# is started or what the project folder is called.
if __name__ == "__main__" and not __package__:
    import runpy
    _here = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_here)
    _pkg = os.path.basename(_here)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    runpy.run_module(f"{_pkg}.app", run_name="__main__", alter_sys=True)
    sys.exit(0)

# Ensure the parent directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import settings
from .updater import create_and_start_updater

# ─── Version ──────────────────────────────────────────────────────────────────
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
try:
    with open(VERSION_FILE) as f:
        __version__ = f.read().strip()
except:
    __version__ = "0.0.0"


def _setup_logging():
    """Configure rotating file logger for production."""
    from .config import settings
    log_dir = os.path.join(settings.BASE_PATH, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "ixope.log")

    handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=3)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Also log to stdout for development
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    stdout_handler.setLevel(logging.WARNING)
    root_logger.addHandler(stdout_handler)


class _ModulePreloader(threading.Thread):
    """Preload heavy application modules while the boot splash is visible."""

    def __init__(self):
        super().__init__(daemon=True, name="ModulePreloader")
        self.ready = threading.Event()
        self.error = None

    def run(self):
        try:
            import importlib
            # Use this module's actual package name (e.g. "ixope" / "tk_ixope")
            # so preloading works regardless of the project folder name.
            pkg = __package__ or "ixope"
            importlib.import_module(f"{pkg}.camera.camera_manager")
            importlib.import_module(f"{pkg}.camera.recording")
            importlib.import_module(f"{pkg}.hardware.led_controller")
            importlib.import_module(f"{pkg}.network.ip_sender")
            importlib.import_module(f"{pkg}.storage.file_manager")
        except Exception as exc:
            self.error = exc
        finally:
            self.ready.set()


class BootSplash:
    """Fullscreen boot splash window with optional animated GIF."""

    def __init__(self, root):
        self.root = root
        self.root.title("IXOPE Boot")
        self.root.geometry(f"{settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}")
        self.root.configure(bg="black")
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(
            root,
            width=settings.WINDOW_WIDTH,
            height=settings.WINDOW_HEIGHT,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack()

        self._frames = []
        self._frame_index = 0
        self._photo = None
        self._load_frames()
        self._message = self.canvas.create_text(
            settings.WINDOW_WIDTH // 2,
            settings.WINDOW_HEIGHT - 40,
            text="Starting IXOPE...",
            fill="white",
            font=("Arial", 12, "bold"),
        )
        self._animate()

    def _load_frames(self):
        gif_path = settings.BOOT_SPLASH_GIF
        if os.path.isfile(gif_path):
            index = 0
            while True:
                try:
                    frame = tk.PhotoImage(file=gif_path, format=f"gif -index {index}")
                except tk.TclError:
                    break
                self._frames.append(frame)
                index += 1
        if not self._frames:
            self._frames.append(tk.PhotoImage(width=settings.WINDOW_WIDTH, height=settings.WINDOW_HEIGHT))
            self.canvas.create_rectangle(0, 0, settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT, fill="black", outline="")
            self.canvas.create_text(
                settings.WINDOW_WIDTH // 2,
                settings.WINDOW_HEIGHT // 2,
                text="IXOPE",
                fill="white",
                font=("Arial", 32, "bold"),
            )
        self._photo = self._frames[0]
        self._img_item = self.canvas.create_image(
            settings.WINDOW_WIDTH // 2,
            settings.WINDOW_HEIGHT // 2,
            image=self._photo,
        )

    def _animate(self):
        if self._frames:
            self.canvas.itemconfig(self._img_item, image=self._frames[self._frame_index])
            self._frame_index = (self._frame_index + 1) % len(self._frames)
        self.root.after(100, self._animate)

    def set_message(self, text):
        self.canvas.itemconfig(self._message, text=text)

    def destroy(self):
        self.canvas.destroy()


def main():
    """Application entry point."""
    # ─── Pre-boot optimizations ───────────────────────────────────────────
    gc.disable()

    try:
        nice = getattr(os, "nice", None)
        if callable(nice):
            nice(-10)
    except (PermissionError, OSError):
        pass

    # ─── Logging ──────────────────────────────────────────────────────────
    _setup_logging()
    log = logging.getLogger("ixope")
    log.info(f"═══ IXOPE Medical v{__version__} starting ═══")
    log.info(f"Python {sys.version.split()[0]}, PID {os.getpid()}")

    # ─── Import and start ─────────────────────────────────────────────────
    from .ui import MedicalUI
    root = tk.Tk()
    root.tk.call('tk', 'scaling', 1.0)

    splash = BootSplash(root)
    root.update_idletasks()
    root.update()

    preloader = _ModulePreloader()
    preloader.start()

    app_ref: list[Any] = [None]

    def _finish_startup():
        if not preloader.ready.is_set():
            root.after(50, _finish_startup)
            return

        if preloader.error:
            log.critical("Boot preload failed: %s", preloader.error, exc_info=True)
            splash.set_message("Startup error, check logs")
            return

        splash.set_message("Initializing interface...")
        try:
            app_ref[0] = MedicalUI(root)
        except Exception as exc:
            log.critical("Failed to create MedicalUI: %s", exc, exc_info=True)
            splash.set_message("UI initialization failed")
            return

        splash.destroy()
        log.info("UI initialized, entering main loop")

        try:
            create_and_start_updater()
        except Exception:
            log.warning("OTA updater could not be started", exc_info=True)

    root.after(50, _finish_startup)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        log.info("Keyboard interrupt, shutting down")
        if app_ref[0] is not None:
            app_ref[0]._shutdown()
    finally:
        gc.enable()
        log.info("═══ IXOPE shutdown complete ═══")


if __name__ == "__main__":
    main()
