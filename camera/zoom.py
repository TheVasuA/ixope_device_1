"""
Zoom and image processing - applied to frames before display.

Key optimizations:
- Uses cv2.resize with INTER_LINEAR (fastest interpolation)
- Pre-calculates crop coordinates
- Avoids creating new arrays when zoom=1.0
"""
import cv2
import numpy as np


def apply_zoom(frame, zoom_level, center_x=None, center_y=None):
    """Apply digital zoom by cropping and resizing. Returns frame (no copy if zoom=1)."""
    if frame is None or zoom_level <= 1.0:
        return frame

    h, w = frame.shape[:2]
    if center_x is None:
        center_x = w // 2
    if center_y is None:
        center_y = h // 2

    crop_w = int(w / zoom_level)
    crop_h = int(h / zoom_level)

    x1 = max(0, min(center_x - crop_w // 2, w - crop_w))
    y1 = max(0, min(center_y - crop_h // 2, h - crop_h))

    cropped = frame[y1:y1 + crop_h, x1:x1 + crop_w]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)


def apply_brightness(frame, level):
    """Apply brightness. level=0.5 is neutral."""
    if frame is None or abs(level - 0.5) < 0.02:
        return frame
    scale = 0.2 + level * 1.6 if level < 0.5 else 1.0 + (level - 0.5) * 1.6
    return cv2.convertScaleAbs(frame, alpha=scale, beta=0)


def apply_contrast(frame, level):
    """Apply contrast. level=0.5 is neutral."""
    if frame is None or abs(level - 0.5) < 0.02:
        return frame
    alpha = 0.3 + level * 1.4 if level < 0.5 else 1.0 + (level - 0.5) * 1.4
    mean = np.mean(frame, axis=(0, 1), keepdims=True)
    result = np.clip((frame.astype(np.float32) - mean) * alpha + mean, 0, 255)
    return result.astype(np.uint8)


def apply_sharpness(frame, level):
    """Apply sharpening. level=0 is no sharpening."""
    if frame is None or level < 0.05:
        return frame
    strength = level * 2.0
    kernel = np.array([
        [-strength / 8, -strength / 8, -strength / 8],
        [-strength / 8, 1 + strength, -strength / 8],
        [-strength / 8, -strength / 8, -strength / 8]
    ], dtype=np.float32)
    return cv2.filter2D(frame, -1, kernel)


def apply_exposure(frame, level):
    """Apply exposure. level=0.5 is neutral."""
    if frame is None or abs(level - 0.5) < 0.02:
        return frame
    if level < 0.5:
        gamma = 0.5 + level
        lut = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
        return cv2.LUT(frame, lut)
    else:
        scale = 1.0 + (level - 0.5) * 1.5
        return cv2.convertScaleAbs(frame, alpha=scale, beta=0)
