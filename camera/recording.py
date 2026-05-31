"""
Video Recorder - Writes frames from the shared camera buffer to disk.

Key optimizations:
- Dedicated recording thread (never blocks UI)
- Grabs frames from CameraManager directly
- Pre-opens VideoWriter before recording starts
- Auto-stop after configurable duration
"""
import cv2
import os
import threading
import time
from datetime import datetime
from ..config import settings


class Recorder:
    """Non-blocking video recorder that pulls frames from CameraManager."""

    def __init__(self, camera_manager):
        self._camera = camera_manager
        self._writer = None
        self._thread = None
        self._recording = False
        self._video_path = None
        self._start_time = 0
        self._frame_count = 0
        self._lock = threading.Lock()

    @property
    def is_recording(self):
        return self._recording

    @property
    def elapsed_seconds(self):
        if self._recording:
            return int(time.time() - self._start_time)
        return 0

    @property
    def video_path(self):
        return self._video_path

    def start(self, scope_name):
        """
        Start recording. Returns True on success.
        Recording runs in its own thread pulling frames from camera.
        """
        if self._recording:
            return False

        if not self._camera.is_available:
            return False

        # Determine save path
        save_folder = settings.SCOPE_VIDEO_FOLDERS.get(scope_name, settings.VIDEO_BASE)
        os.makedirs(save_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = scope_name.upper() if scope_name else "GENERAL"
        filename = f"{prefix}_VIDEO_{timestamp}.mp4"
        self._video_path = os.path.join(save_folder, filename)

        # Get frame dimensions
        frame = self._camera.get_frame()
        if frame is None:
            return False

        h, w = frame.shape[:2]

        # Try codecs until one works
        for codec in settings.VIDEO_CODECS:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(self._video_path, fourcc, settings.VIDEO_FPS, (w, h))
                if writer.isOpened():
                    self._writer = writer
                    break
                writer.release()
            except:
                continue

        if self._writer is None:
            return False

        self._recording = True
        self._start_time = time.time()
        self._frame_count = 0

        # Start recording thread
        self._thread = threading.Thread(target=self._record_loop, daemon=True, name="VideoRecorder")
        self._thread.start()

        print(f"Recording started: {self._video_path}")
        return True

    def stop(self):
        """Stop recording. Returns the saved video path."""
        if not self._recording:
            return None

        self._recording = False

        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

        if self._writer:
            self._writer.release()
            self._writer = None

        path = self._video_path
        print(f"Recording stopped: {path} ({self._frame_count} frames)")
        return path

    def _record_loop(self):
        """Dedicated recording thread - grabs frames at video FPS."""
        interval = 1.0 / settings.VIDEO_FPS
        last_frame_id = -1

        while self._recording:
            # Auto-stop after max duration
            if time.time() - self._start_time >= settings.MAX_RECORD_SECONDS:
                self._recording = False
                break

            # Only write if we have a new frame
            frame_id = self._camera.get_frame_id()
            if frame_id != last_frame_id:
                frame = self._camera.get_frame_copy()
                if frame is not None and self._writer:
                    self._writer.write(frame)
                    self._frame_count += 1
                    last_frame_id = frame_id

            # Sleep to match target FPS (avoid busy-waiting)
            time.sleep(interval)

        # Final cleanup
        if self._writer:
            self._writer.release()
            self._writer = None
