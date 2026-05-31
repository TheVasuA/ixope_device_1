"""
File Manager - handles image capture saving and server upload.
All I/O runs in background threads. Production-grade with disk checks.
"""
import os
import shutil
import cv2
import logging
import threading
import requests
from datetime import datetime
from ..config import settings

log = logging.getLogger(__name__)

# Minimum free disk space required to save (100 MB)
MIN_FREE_SPACE_MB = 100


class FileManager:
    """Manages saving captured images/videos and uploading to server."""

    def __init__(self):
        self._ensure_folders()

    def _ensure_folders(self):
        """Create all required directories."""
        os.makedirs(settings.IMAGE_BASE, exist_ok=True)
        os.makedirs(settings.VIDEO_BASE, exist_ok=True)
        for folder in settings.SCOPE_IMAGE_FOLDERS.values():
            os.makedirs(folder, exist_ok=True)
        for folder in settings.SCOPE_VIDEO_FOLDERS.values():
            os.makedirs(folder, exist_ok=True)

    @staticmethod
    def check_disk_space():
        """Check if enough disk space is available. Returns (ok, free_mb)."""
        try:
            usage = shutil.disk_usage(settings.BASE_PATH)
            free_mb = usage.free / (1024 * 1024)
            return free_mb >= MIN_FREE_SPACE_MB, free_mb
        except:
            return True, 999  # Assume OK if check fails

    def save_image(self, frame, scope_name, callback=None):
        """
        Save image in background thread. Frame must be BGR (from camera directly).
        callback(success, path) is called on completion.
        """
        if frame is None:
            if callback:
                callback(False, None)
            return

        # Check disk space before spawning thread
        ok, free = self.check_disk_space()
        if not ok:
            log.warning(f"Low disk space: {free:.0f}MB free, need {MIN_FREE_SPACE_MB}MB")
            if callback:
                callback(False, None)
            return

        thread = threading.Thread(
            target=self._save_image_worker,
            args=(frame.copy(), scope_name, callback),
            daemon=True
        )
        thread.start()

    def _save_image_worker(self, frame, scope_name, callback):
        """Worker thread for saving and uploading image."""
        try:
            # Determine save path
            folder = settings.SCOPE_IMAGE_FOLDERS.get(scope_name, settings.IMAGE_BASE)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = scope_name.upper() if scope_name else "GENERAL"
            filename = f"{prefix}_{timestamp}.jpg"
            full_path = os.path.join(folder, filename)

            # Save locally
            success = cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])

            if callback:
                callback(success, full_path)

            if success:
                # Upload in same thread (already background)
                self._upload_image(full_path, scope_name)

        except Exception as e:
            print(f"Save image error: {e}")
            if callback:
                callback(False, None)

    def _upload_image(self, file_path, scope_name):
        """Upload image to server."""
        try:
            url = f"{settings.SERVER_URL}/upload.php?id={settings.DEVICE_ID}"
            with open(file_path, 'rb') as f:
                files = {'file': (f'{scope_name}.jpg', f)}
                resp = requests.post(url, files=files, timeout=30)
                if resp.status_code == 200:
                    print(f"Upload OK: {os.path.basename(file_path)}")
                else:
                    print(f"Upload failed: {resp.status_code}")
        except requests.exceptions.ConnectionError:
            print("Upload: no network")
        except Exception as e:
            print(f"Upload error: {e}")

    def upload_video(self, video_path, scope_name, callback=None):
        """Upload video in background thread."""
        if not video_path or not os.path.exists(video_path):
            if callback:
                callback(False)
            return

        thread = threading.Thread(
            target=self._upload_video_worker,
            args=(video_path, scope_name, callback),
            daemon=True
        )
        thread.start()

    def _upload_video_worker(self, video_path, scope_name, callback):
        """Worker for video upload."""
        try:
            url = f"{settings.SERVER_URL}/upload1.php?id={settings.DEVICE_ID}"
            with open(video_path, 'rb') as f:
                files = {'file': (f'{scope_name}.mp4', f)}
                resp = requests.post(url, files=files, timeout=120)
                success = resp.status_code == 200
                if callback:
                    callback(success)
        except Exception as e:
            print(f"Video upload error: {e}")
            if callback:
                callback(False)

    @staticmethod
    def list_images(scope_name):
        """List images for a scope."""
        folder = settings.SCOPE_IMAGE_FOLDERS.get(scope_name, settings.IMAGE_BASE)
        if not os.path.exists(folder):
            return []

        images = []
        try:
            for f in sorted(os.listdir(folder), reverse=True):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    path = os.path.join(folder, f)
                    try:
                        images.append({
                            'filename': f,
                            'path': f'/image/{scope_name}/{f}',
                            'scope': scope_name,
                            'size': os.path.getsize(path),
                            'created': datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                        })
                    except:
                        continue
        except Exception as e:
            print(f"list_images error ({scope_name}): {e}")
        return images

    @staticmethod
    def list_videos(scope_name=None):
        """List videos, optionally filtered by scope."""
        videos = []

        # Check scope-specific video folders
        if scope_name and scope_name in settings.SCOPE_VIDEO_FOLDERS:
            folders_to_check = [settings.SCOPE_VIDEO_FOLDERS[scope_name]]
        elif scope_name is None:
            # Check all scope folders + base folder
            folders_to_check = list(settings.SCOPE_VIDEO_FOLDERS.values()) + [settings.VIDEO_BASE]
        else:
            folders_to_check = [settings.VIDEO_BASE]

        seen = set()
        for folder in folders_to_check:
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                if not f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                    continue
                if f in seen:
                    continue
                seen.add(f)
                path = os.path.join(folder, f)
                try:
                    videos.append({
                        'filename': f,
                        'path': f'/video/{f}',
                        'scope': scope_name or '',
                        'size': os.path.getsize(path),
                        'created': datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                    })
                except:
                    continue

        videos.sort(key=lambda x: x['created'], reverse=True)
        return videos
