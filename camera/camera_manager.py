"""
Camera Manager - Ultra-low-latency USB camera capture with shared frame buffer.

Key optimizations:
- Single frame buffer with lock (no queue overhead for latest-frame access)
- Pre-allocated numpy buffer to avoid per-frame allocation
- MJPG codec for hardware-accelerated decode
- Buffer size = 1 to always get freshest frame
- Shared frame reference for UI, recording, and streaming
"""
import cv2
import threading
import time
import numpy as np
import glob
from ..config import settings


class CameraManager:
    """
    Manages USB camera capture in a dedicated thread.
    Provides zero-copy frame access via a shared buffer.
    """

    def __init__(self, camera_index=None):
        self._cap = None
        self._camera_index = None
        self._running = False
        self._thread = None

        # Shared frame buffer - single allocation, overwritten each capture
        self._frame_lock = threading.Lock()
        self._current_frame = None
        self._frame_id = 0  # Monotonic counter to detect new frames

        # Stats
        self._fps_actual = 0.0
        self._frame_count = 0
        self._last_fps_time = time.time()

        self._init_camera(camera_index)

    def _init_camera(self, camera_index):
        """Detect and initialize USB camera with optimal settings."""
        import os
        print("\n=== USB Camera Detection ===")

        # Platform-specific backend
        if os.name == 'posix':
            video_devices = glob.glob('/dev/video*')
            print(f"Available: {video_devices}")
            backend = cv2.CAP_V4L2
        else:
            # Windows: use DirectShow for webcam access
            video_devices = ['(DirectShow)']
            print(f"Available: {video_devices}")
            backend = cv2.CAP_DSHOW

        indices = [camera_index] if camera_index is not None else range(settings.CAMERA_MAX_INDEX)

        for idx in indices:
            cap = cv2.VideoCapture(idx, backend)
            if not cap.isOpened():
                cap.release()
                continue

            # Force MJPG for hardware decode (much faster than YUYV on Linux;
            # on Windows DirectShow may ignore this — that's fine)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, settings.CAMERA_FPS)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, settings.CAMERA_BUFFER_SIZE)

            # Brief warmup
            time.sleep(0.3)

            ret, frame = cap.read()
            if ret and frame is not None:
                self._cap = cap
                self._camera_index = idx
                self._current_frame = frame
                print(f"✓ Camera {idx} ready: {frame.shape}")
                break
            else:
                cap.release()

        if self._cap is None:
            print("✗ No USB camera found")
            return

        print(f"=== Camera Ready (index {self._camera_index}) ===\n")

    @property
    def is_available(self):
        return self._cap is not None

    @property
    def fps(self):
        return self._fps_actual

    def start(self):
        """Start the capture thread."""
        if not self.is_available or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraCapture")
        self._thread.start()

    def stop(self):
        """Stop capture and release resources."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap:
            self._cap.release()
            self._cap = None

    def get_frame(self):
        """
        Get the latest frame (reference, not copy).
        Returns None if no frame available.
        
        IMPORTANT: Caller must NOT modify the returned array.
        If modification is needed, caller should copy explicitly.
        """
        with self._frame_lock:
            return self._current_frame

    def get_frame_copy(self):
        """Get a copy of the latest frame (for recording/saving)."""
        with self._frame_lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
            return None

    def get_frame_id(self):
        """Get current frame ID to detect if frame changed."""
        return self._frame_id

    def _capture_loop(self):
        """Main capture loop - runs in dedicated thread."""
        consecutive_failures = 0

        while self._running:
            ret, frame = self._cap.read()

            if ret and frame is not None:
                consecutive_failures = 0
                with self._frame_lock:
                    self._current_frame = frame  # Direct assignment, no copy
                    self._frame_id += 1

                # FPS tracking
                self._frame_count += 1
                now = time.time()
                elapsed = now - self._last_fps_time
                if elapsed >= 1.0:
                    self._fps_actual = self._frame_count / elapsed
                    self._frame_count = 0
                    self._last_fps_time = now
            else:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    print("Camera: Too many failures, attempting reconnect...")
                    self._reconnect()
                    consecutive_failures = 0
                time.sleep(0.01)

    def _reconnect(self):
        """Attempt to reconnect camera with retry."""
        if self._cap:
            try:
                self._cap.release()
            except:
                pass
            self._cap = None
        # Wait before retry
        time.sleep(2)
        self._init_camera(self._camera_index)
        if self._cap is None:
            # Try again with auto-detect
            time.sleep(3)
            self._init_camera(None)

    # ─── Focus Control ────────────────────────────────────────────────────────

    def get_focus_info(self):
        """Get focus capabilities."""
        if not self._cap:
            return {'auto_supported': False, 'manual_supported': False}

        info = {'auto_supported': False, 'manual_supported': False, 'current': 0}
        try:
            af = self._cap.get(cv2.CAP_PROP_AUTOFOCUS)
            info['auto_supported'] = af is not None and af != -1

            focus = self._cap.get(cv2.CAP_PROP_FOCUS)
            info['manual_supported'] = focus is not None and focus != -1
            info['current'] = focus if info['manual_supported'] else 0
        except:
            pass
        return info

    def set_autofocus(self, enabled):
        """Enable/disable autofocus."""
        if self._cap:
            return self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if enabled else 0)
        return False

    def set_focus(self, value):
        """Set manual focus value (0-255)."""
        if self._cap:
            self._cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            return self._cap.set(cv2.CAP_PROP_FOCUS, int(value))
        return False
