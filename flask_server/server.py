"""
Flask Server - Lightweight HTTP server for live streaming and file access.

Key optimizations:
- Shares camera frame directly (no extra copy for streaming)
- JPEG encoding at reduced quality for speed
- Threaded mode for concurrent requests
- Pre-built HTML templates (no runtime rendering)
- Lucide SVG icons (no external CDN)
"""
import cv2
import time
import os
import re
from flask import Flask, Response, jsonify, send_file, request
from datetime import datetime
from ..config import settings
from ..storage import FileManager
from .templates import INDEX_HTML, IMAGES_HTML, VIDEOS_HTML


_app = Flask(__name__)
_camera_ref = None  # Set by start_server()


def start_server(camera_manager):
    """Start Flask server. Called from background thread."""
    global _camera_ref
    _camera_ref = camera_manager
    
    # Try the configured port, then fallback ports
    ports_to_try = [settings.FLASK_PORT, 5001, 5002, 8080]
    
    for port in ports_to_try:
        try:
            print(f"Flask server trying port {port}...")
            _app.run(
                host=settings.FLASK_HOST,
                port=port,
                threaded=True,
                debug=False,
                use_reloader=False
            )
            break  # If run() returns normally (shouldn't), break
        except OSError as e:
            if "Address already in use" in str(e) or "address already in use" in str(e):
                print(f"Port {port} in use, trying next...")
                continue
            else:
                print(f"Flask server error: {e}")
                break
        except Exception as e:
            print(f"Flask server error: {e}")
            break


# ─── Page Routes ─────────────────────────────────────────────────────────────

@_app.route('/')
def index():
    return INDEX_HTML


@_app.route('/images')
def images_page():
    return IMAGES_HTML


@_app.route('/videos')
def videos_page():
    return VIDEOS_HTML


@_app.route('/scope/<scope>')
def scope_page(scope):
    if scope not in settings.SCOPE_IMAGE_FOLDERS:
        return jsonify({'error': 'not found'}), 404
    # Reuse images page with scope filter pre-applied
    return IMAGES_HTML


# ─── API Routes ──────────────────────────────────────────────────────────────

@_app.route('/live_feed')
def live_feed():
    return Response(_generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@_app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'camera': 'available' if _camera_ref and _camera_ref.is_available else 'unavailable',
        'timestamp': datetime.now().isoformat()
    })


@_app.route('/api/images')
def api_images():
    all_imgs = []
    for scope in settings.SCOPE_IMAGE_FOLDERS:
        all_imgs.extend(FileManager.list_images(scope))
    all_imgs.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(all_imgs)


@_app.route('/api/videos')
def api_videos():
    videos = FileManager.list_videos()
    videos.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(videos)


@_app.route('/scope/<scope>/stats')
def scope_stats(scope):
    if scope not in settings.SCOPE_IMAGE_FOLDERS:
        return jsonify({'error': 'not found'}), 404
    images = FileManager.list_images(scope)
    videos = FileManager.list_videos(scope)
    return jsonify({'scope': scope, 'images': len(images), 'videos': len(videos)})


@_app.route('/scope/<scope>/images')
def scope_images(scope):
    if scope not in settings.SCOPE_IMAGE_FOLDERS:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'images': FileManager.list_images(scope)})


@_app.route('/scope/<scope>/videos')
def scope_videos(scope):
    if scope not in settings.SCOPE_IMAGE_FOLDERS:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'videos': FileManager.list_videos(scope)})


@_app.route('/image/<scope>/<filename>')
def get_image(scope, filename):
    folder = settings.SCOPE_IMAGE_FOLDERS.get(scope)
    if not folder:
        return jsonify({'error': 'not found'}), 404
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'not found'}), 404
    if 'download' in request.args:
        return send_file(path, as_attachment=True, download_name=filename)
    return send_file(path)


@_app.route('/video/<filename>', methods=['GET', 'DELETE'])
def handle_video(filename):
    # Search all video folders (base + scope subfolders)
    path = _find_video(filename)

    if request.method == 'DELETE':
        if path:
            os.remove(path)
            return jsonify({'message': f'{filename} deleted'})
        return jsonify({'error': 'not found'}), 404

    if not path:
        return jsonify({'error': 'not found'}), 404

    if 'download' in request.args:
        return send_file(path, as_attachment=True, download_name=filename)

    # Range request support for video seeking
    range_header = request.headers.get('Range')
    if range_header:
        return _range_response(path, range_header)

    resp = send_file(path)
    resp.headers['Accept-Ranges'] = 'bytes'
    return resp


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _find_video(filename):
    """Search all video folders for a filename. Returns full path or None."""
    # Check base folder first
    path = os.path.join(settings.VIDEO_BASE, filename)
    if os.path.exists(path):
        return path
    # Check scope subfolders
    for folder in settings.SCOPE_VIDEO_FOLDERS.values():
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
    return None


def _generate_frames():
    """Generator for MJPEG stream. Shares frame from camera manager."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, settings.STREAM_JPEG_QUALITY]

    while True:
        if _camera_ref and _camera_ref.is_available:
            frame = _camera_ref.get_frame()  # No copy - read only
            if frame is not None:
                ret, buf = cv2.imencode('.jpg', frame, encode_params)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.033)  # ~30fps cap


def _range_response(path, range_header):
    """Handle HTTP range requests for video seeking."""
    size = os.path.getsize(path)
    match = re.search(r'(\d+)-(\d*)', range_header)
    if not match:
        return send_file(path)

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else size - 1
    end = min(end, size - 1)
    length = end - start + 1

    with open(path, 'rb') as f:
        f.seek(start)
        data = f.read(length)

    resp = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
    resp.headers['Content-Range'] = f'bytes {start}-{end}/{size}'
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Length'] = str(length)
    return resp
