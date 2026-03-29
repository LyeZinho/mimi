"""Pose Extractor Flask Server.

Start: python server.py
Open: http://localhost:5001
"""

import base64
import io
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agent.ml.keyframe_storage import KeyframeStorage
from agent.ml.pose_rotation import BONE_HIERARCHY, PoseRotationCalculator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pose_extractor")

app = Flask(__name__, static_folder="static")
CORS(app)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_TMP_DIR = Path(__file__).resolve().parent / "tmp"
_VROID_MODELS_DIR = Path(_project_root) / "vroid_model"
_VROID_ANIMATIONS_DIR = _VROID_MODELS_DIR / "animations"

_TMP_DIR.mkdir(parents=True, exist_ok=True)
_VROID_ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)


# Skeleton connections for drawing
SKELETON_CONNECTIONS = [
    (11, 13), (13, 15), (12, 14), (14, 16),  # arms
    (11, 12), (23, 24),  # shoulders, hips
    (23, 25), (25, 27), (24, 26), (26, 28),  # legs
    (11, 23), (12, 24),  # torso sides
]

# Connections for tracking mode (no nose - index 0)
TRACKING_CONNECTIONS = SKELETON_CONNECTIONS

# Colors for skeleton
COLOR_DETECTED = (0, 255, 0)  # green
COLOR_MISSING = (255, 0, 0)   # red


def draw_skeleton_on_frame(frame: np.ndarray, landmarks: list, w: int, h: int) -> bytes:
    """Draw skeleton overlay on a video frame, return as JPEG bytes."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return b""

    img = Image.fromarray(frame)
    img = img.resize((w, h))
    draw = ImageDraw.Draw(img)

    # Scale landmarks to image size
    pts = []
    for lm in landmarks:
        x = int(lm.get("x", 0) * w)
        y = int(lm.get("y", 0) * h)
        pts.append((x, y))

    # Draw connections
    for (a, b) in SKELETON_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            draw.line([pts[a], pts[b]], fill=COLOR_DETECTED, width=2)

    # Draw joints
    for i, (x, y) in enumerate(pts):
        r = 4
        draw.ellipse([x - r, y - r, x + r, y + r], fill=COLOR_DETECTED)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return buf.getvalue()


# Routes
@app.route("/")
def index():
    return send_from_directory(str(_STATIC_DIR), "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(str(_STATIC_DIR), filename)


@app.route("/vrm/<filename>")
def vrm_file(filename):
    return send_from_directory(str(_VROID_MODELS_DIR), filename)


@app.route("/vrm-at-path")
def vrm_at_path():
    from flask import abort
    file_path = request.args.get("path", "")
    if not file_path:
        abort(400, "Missing 'path' query parameter")
    p = Path(file_path).resolve()
    if not p.exists():
        abort(404, f"File not found: {p}")
    return send_from_directory(str(p.parent), p.name)


@app.route("/models")
def list_models():
    vrms = sorted(_VROID_MODELS_DIR.glob("*.vrm"))
    poses = sorted(_VROID_ANIMATIONS_DIR.iterdir()) if _VROID_ANIMATIONS_DIR.exists() else []
    return jsonify({
        "vrms": [str(p.name) for p in vrms],
        "poses": [p.name for p in poses if p.is_dir()],
    })


@app.route("/preview", methods=["POST"])
def preview():
    """Get a single frame preview with skeleton overlay.

    POST body: { "video_path": "...", "timestamp": 0.5 }
    Returns: { "image": "base64...", "landmarks": [...], "timestamp": 0.5 }
    """
    data = request.get_json(force=True)
    video_path = data.get("video_path", "")
    timestamp = float(data.get("timestamp", 0))

    if not video_path or not Path(video_path).exists():
        return jsonify({"error": f"Video not found: {video_path}"}), 400

    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = int(timestamp * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return jsonify({"error": "Could not read frame"}), 400

        # Detect pose
        from agent.ml.pose_detector import PoseDetector
        detector = PoseDetector(static_image_mode=True)
        result = detector.process_frame(frame)
        detector.close()

        h, w = 480, 640
        landmarks = []
        if result and result.get("body_landmarks"):
            landmarks = result["body_landmarks"].get("landmarks", [])

        # Draw skeleton
        img_bytes = draw_skeleton_on_frame(frame, landmarks, w, h)
        img_b64 = base64.b64encode(img_bytes).decode() if img_bytes else ""

        return jsonify({
            "image": f"data:image/jpeg;base64,{img_b64}",
            "landmarks": landmarks,
            "timestamp": timestamp,
            "frame": frame_idx,
            "duration": float(cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps) if cap else 0,
        })
    except Exception as e:
        logger.error(f"Preview error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/video-info", methods=["POST"])
def video_info():
    """Get video duration and frame count for trim controls."""
    data = request.get_json(force=True)
    video_path = data.get("video_path", "")

    if not video_path or not Path(video_path).exists():
        return jsonify({"error": f"Video not found: {video_path}"}), 400

    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        return jsonify({
            "fps": fps,
            "total_frames": total_frames,
            "duration": round(duration, 2),
            "width": width,
            "height": height,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/first-frame", methods=["POST"])
def first_frame():
    """Get the first frame (or frame at timestamp) as base64 image for manual point placement.

    POST body: { "video_path": "...", "timestamp": 0.0 }
    Returns: { "image": "data:image/jpeg;base64,...", "width": 640, "height": 480 }
    """
    data = request.get_json(force=True)
    video_path = data.get("video_path", "")
    timestamp = float(data.get("timestamp", 0))

    if not video_path or not Path(video_path).exists():
        return jsonify({"error": f"Video not found: {video_path}"}), 400

    try:
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = int(timestamp * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if not ret:
            return jsonify({"error": "Could not read frame"}), 400

        # Resize to max 640x480 for display
        max_w, max_h = 640, 480
        scale = min(max_w / width, max_h / height, 1.0)
        disp_w = int(width * scale)
        disp_h = int(height * scale)
        display_frame = cv2.resize(frame, (disp_w, disp_h))

        _, buf = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        img_b64 = base64.b64encode(buf.tobytes()).decode()

        return jsonify({
            "image": f"data:image/jpeg;base64,{img_b64}",
            "width": disp_w,
            "height": disp_h,
            "original_width": width,
            "original_height": height,
            "scale": scale,
        })
    except Exception as e:
        logger.error(f"First frame error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 11 essential skeleton points for manual placement
TRACKED_POINTS = [
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
]

# MediaPipe indices for each tracked point
TRACKED_POINT_INDICES = {
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}


@app.route("/track", methods=["POST"])
def track():
    """Track manually placed keypoints through video using Lucas-Kanade optical flow.

    POST body: {
        "video_path": "...",
        "pose_name": "walk",
        "points": {"left_shoulder": [x, y], ...},  // in display coords
        "display_width": 640,
        "display_height": 480,
        "start_time": 0.0,
        "end_time": -1.0
    }

    Returns SSE stream with tracked frames and bone rotations.
    """
    data = request.get_json(force=True)
    video_path = data.get("video_path", "")
    pose_name = data.get("pose_name", "track_pose")
    points = data.get("points", {})
    disp_w = int(data.get("display_width", 640))
    disp_h = int(data.get("display_height", 480))
    start_time = float(data.get("start_time", 0))
    end_time = float(data.get("end_time", -1))

    if not video_path or not Path(video_path).exists():
        return jsonify({"error": f"Video not found: {video_path}"}), 400

    if len(points) < 6:
        return jsonify({"error": "Need at least 6 points placed"}), 400

    def generate():
        yield f"data: {json.dumps({'type': 'start', 'pose_name': pose_name})}\n\n"
        try:
            for chunk in _track_with_flow(video_path, pose_name, points, disp_w, disp_h, start_time, end_time):
                yield chunk
        except Exception as e:
            logger.error(f"Tracking error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _track_with_flow(video_path, pose_name, points, disp_w, disp_h, start_time, end_time):
    """Core tracking pipeline with multi-pass refinement and anatomical validation."""
    import cv2

    from agent.ml.keyframe_storage import KeyframeStorage as KFS
    from agent.ml.pose_rotation import PoseRotationCalculator

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    scale_x = orig_w / disp_w
    scale_y = orig_h / disp_h

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps) if end_time > 0 else total_frames
    end_frame = min(end_frame, total_frames)

    point_names = sorted(points.keys())
    n_points = len(point_names)

    # Convert display coords to original video coords
    initial_pts = np.array([
        [points[name][0] * scale_x, points[name][1] * scale_y]
        for name in point_names
    ], dtype=np.float32)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, first_frame = cap.read()
    if not ret:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Cannot read start frame'})}\n\n"
        return

    rotator = PoseRotationCalculator()
    rotator.set_auto_rest_pose()

    output_dir = str(_TMP_DIR / pose_name)
    storage = KFS(base_path=Path(output_dir), name=pose_name, mode="w", fps=fps)

    # Optical flow parameters
    lk_params = dict(winSize=(31, 31), maxLevel=4,
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.001))

    # Anatomical constraints (in original video pixels)
    max_velocity = orig_w * 0.15  # max movement per frame = 15% of frame width
    min_bone_length = orig_w * 0.02  # minimum bone length
    max_bone_length = orig_w * 0.4   # maximum bone length

    # Limb pair ratios for anatomical check (should be ~1:1)
    limb_pairs = {
        ('left_elbow', 'left_wrist', 'left_shoulder', 'left_elbow'),
        ('right_elbow', 'right_wrist', 'right_shoulder', 'right_elbow'),
        ('left_knee', 'left_ankle', 'left_hip', 'left_knee'),
        ('right_knee', 'right_ankle', 'right_hip', 'right_knee'),
    }

    total_frames_trimmed = end_frame - start_frame
    total_frames_trimmed = max(1, total_frames_trimmed)

    # === PASS 1: Raw tracking (with frame skip for speed) ===
    frame_skip = max(1, total_frames_trimmed // 500)  # aim for ~500 key frames max
    yield f"data: {json.dumps({'type': 'status', 'message': f'Pass 1/3: Tracking (skip={frame_skip})...'})}\n\n"

    # Callback for sending preview frames during tracking
    def send_preview_frame(small_frame, good_pts, n_points, processed, elapsed, small_w, small_h):
        import base64
        lm_dicts = [{"x": float(good_pts[j, 0] / small_w), "y": float(good_pts[j, 1] / small_h), "z": 0.0} for j in range(min(len(good_pts), n_points))]
        img_bytes = draw_skeleton_on_frame(small_frame, lm_dicts, 640, 480)
        if img_bytes:
            img_b64 = base64.b64encode(img_bytes).decode()
            # Use generator yield via closure - we need to make this work
            # Since we can't yield from callback, store preview for later
            preview_queue.append({'image': img_b64, 'frame': processed, 'keyframes': processed, 'tracked': len(good_pts)})

    preview_queue = []
    raw_tracks, scale = _run_optical_flow(cap, start_frame, end_frame, initial_pts, point_names,
                                          lk_params, total_frames_trimmed, max_velocity, frame_skip,
                                          video_path, orig_w, orig_h, yield_fn=send_preview_frame)

    # Send queued preview frames
    for preview in preview_queue:
        img_data = "data:image/jpeg;base64," + preview["image"]
        yield f"data: {json.dumps({'type': 'frame', 'image': img_data, 'frame': preview['frame'], 'keyframes': preview['keyframes'], 'tracked': preview['tracked']})}\n\n"

    tracked_count = len(raw_tracks)
    yield f"data: {json.dumps({'type': 'status', 'message': f'Pass 1 done: {tracked_count} frames tracked'})}\n\n"

    if tracked_count < 2:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Too few frames tracked, try again'})}\n\n"
        return

    # === PASS 2: Interpolate missing frames ===
    yield f"data: {json.dumps({'type': 'status', 'message': 'Interpolating missing frames...'})}\n\n"
    interpolated = _interpolate_tracks(raw_tracks)

    # === PASS 3: Smooth ===
    yield f"data: {json.dumps({'type': 'status', 'message': 'Smoothing tracks...'})}\n\n"
    smoothed_tracks = _smooth_tracks(interpolated, window=5)

    # Scale back to original resolution
    corrected_tracks = {}
    inv_scale = 1.0 / scale
    for frame_idx, pts in smoothed_tracks.items():
        corrected_tracks[frame_idx] = pts * inv_scale

    # === Store final results ===
    yield f"data: {json.dumps({'type': 'status', 'message': 'Storing keyframes...'})}\n\n"

    keyframes_stored = 0
    sorted_frames = sorted(corrected_tracks.keys())
    total_tracked = len(sorted_frames)

    # Sample frames for preview (every 10% of tracked frames)
    preview_interval = max(1, total_tracked // 10)

    for idx, frame_i in enumerate(sorted_frames):
        frame_idx = start_frame + frame_i
        timestamp = frame_idx / fps

        # Read frame only for preview
        should_preview = (idx % preview_interval == 0)
        frame = None
        if should_preview:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                frame = None

        # Get corrected positions
        frame_tracks = corrected_tracks[frame_i]

        # Build landmarks
        landmarks = np.zeros((33, 3), dtype=np.float32)
        for j, name in enumerate(point_names):
            if j < len(frame_tracks):
                mp_idx = TRACKED_POINT_INDICES.get(name)
                if mp_idx is not None and not np.isnan(frame_tracks[j, 0]):
                    landmarks[mp_idx, 0] = frame_tracks[j, 0] / orig_w
                    landmarks[mp_idx, 1] = frame_tracks[j, 1] / orig_h

        _interpolate_missing_joints(landmarks, point_names)

        # Keyframe detection
        is_kf = keyframes_stored == 0
        if not is_kf and idx > 0:
            prev_tracks = corrected_tracks.get(sorted_frames[idx - 1])
            if prev_tracks is not None:
                movement = np.mean(np.abs(frame_tracks - prev_tracks))
                is_kf = movement > orig_w * 0.01

        if is_kf:
            storage.add_keyframe(frame_id=frame_idx, timestamp=timestamp,
                                 landmarks=landmarks, frame_type="key")
            keyframes_stored += 1

        # Preview every 10%
        if should_preview and frame is not None:
            lm_dicts = [{"x": float(lm[0]), "y": float(lm[1]), "z": 0.0} for lm in landmarks]
            img_bytes = draw_skeleton_on_frame(frame, lm_dicts, 640, 480)
            if img_bytes:
                img_b64 = base64.b64encode(img_bytes).decode()
                yield f"data: {json.dumps({'type': 'frame', 'image': f'data:image/jpeg;base64,{img_b64}', 'frame': idx + 1, 'total': total_tracked, 'keyframes': keyframes_stored, 'is_keyframe': bool(is_kf), 'timestamp': float(timestamp), 'pass': 'final'})}\n\n"

        # Progress every 20%
        if idx % (total_tracked // 5 + 1) == 0:
            pct = int((idx + 1) / total_tracked * 100)
            yield f"data: {json.dumps({'type': 'progress', 'frame': idx + 1, 'total': total_tracked, 'pct': pct, 'keyframes': keyframes_stored})}\n\n"

    cap.release()
    storage.finalize()

    result = {
        'type': 'done',
        'result': {
            'success': True,
            'total_frames': total_frames_trimmed,
            'keyframes_stored': keyframes_stored,
            'storage_path': output_dir,
            'pose_name': pose_name,
        }
    }
    yield f"data: {json.dumps(result)}\n\n"


def _run_optical_flow(cap, start_frame, end_frame, initial_pts, point_names,
                      lk_params, total_frames, max_velocity, frame_skip,
                      video_path, orig_w, orig_h, yield_fn=None):
    """Efficient tracking: only processes frames with significant motion. Returns (tracks, scale).
    
    Args:
        yield_fn: Optional callback for sending preview frames. Called with (small_frame, good_pts, n_points, processed, elapsed).
    """
    import cv2
    import time

    n_points = len(point_names)
    total = end_frame - start_frame
    tracks = {}

    # Calculate scale
    scale = min(320.0 / orig_w, 240.0 / orig_h, 1.0)
    small_w, small_h = int(orig_w * scale), int(orig_h * scale)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ret, first_frame = cap.read()
    if not ret:
        return {}, 1.0

    first_small = cv2.resize(first_frame, (small_w, small_h))
    prev_gray = cv2.cvtColor(first_small, cv2.COLOR_BGR2GRAY)

    # Scale initial points to small resolution
    small_pts = initial_pts * scale
    prev_pts = small_pts.reshape(-1, 1, 2)
    tracks[0] = small_pts.copy()

    motion_threshold = 8
    min_motion_frames = 3

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame + 1)
    frame_idx = start_frame + 1
    last_tracked_idx = 0
    processed = 0
    start_time = time.time()
    prev_motion_frame = prev_gray.copy()

    while frame_idx < end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        small = cv2.resize(frame, (small_w, small_h))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        # Motion detection
        motion = np.mean(np.abs(gray.astype(float) - prev_motion_frame.astype(float)))

        should_track = (
            motion > motion_threshold or
            (frame_idx - start_frame) < 5 or
            (frame_idx - last_tracked_idx) > min_motion_frames * 3 or
            frame_idx == start_frame + 1
        )

        if should_track and (frame_idx - last_tracked_idx) >= min_motion_frames:
            valid_mask = ~np.isnan(prev_pts.flatten()).reshape(prev_pts.shape[0], 2).any(axis=1)
            valid_pts = prev_pts[valid_mask]

            if len(valid_pts) >= 6:
                next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, valid_pts, None, **lk_params)

                if next_pts is not None and len(next_pts) == len(valid_pts):
                    next_back, status_back, _ = cv2.calcOpticalFlowPyrLK(gray, prev_gray, next_pts, None, **lk_params)

                    if next_back is not None and len(next_back) == len(next_pts):
                        fb_dist = np.linalg.norm(next_pts - next_back, axis=2).flatten()
                        min_len = min(len(status.flatten()), len(status_back.flatten()), len(fb_dist))
                        good_mask = (status.flatten()[:min_len] == 1) & (status_back.flatten()[:min_len] == 1) & (fb_dist[:min_len] < 5.0)

                        if np.sum(good_mask) >= 6:
                            good_pts = next_pts[:min_len][good_mask].reshape(-1, 2)

                            full_pts = np.full((n_points, 2), np.nan, dtype=np.float32)
                            orig_indices = np.where(valid_mask)[0]
                            good_orig = orig_indices[:min_len][good_mask[:min_len] if min_len <= len(good_mask) else good_mask[:min_len]]

                            for j, gi in enumerate(good_orig):
                                if j < len(good_pts) and gi < n_points:
                                    full_pts[gi] = good_pts[j]

                            tracks[frame_idx - start_frame] = full_pts
                            prev_pts = full_pts.reshape(-1, 1, 2)
                            last_tracked_idx = frame_idx

                            processed += 1

                            # Send preview every 5 tracked frames via callback
                            if yield_fn and processed % 5 == 0:
                                elapsed = time.time() - start_time
                                logger.info(f"Tracked {processed} frames in {elapsed:.1f}s")
                                yield_fn(small, good_pts, n_points, processed, elapsed, small_w, small_h)

        prev_motion_frame = gray.copy()
        prev_gray = gray.copy()
        frame_idx += 1

    elapsed = time.time() - start_time
    logger.info(f"Tracking done: {processed} frames in {elapsed:.1f}s")
    return tracks, scale


def _interpolate_tracks(tracks):
    """Linearly interpolate between tracked frames."""
    if len(tracks) < 2:
        return tracks

    sorted_frames = sorted(tracks.keys())
    interpolated = {}

    for i in range(len(sorted_frames) - 1):
        f1 = sorted_frames[i]
        f2 = sorted_frames[i + 1]
        interpolated[f1] = tracks[f1].copy()

        gap = f2 - f1
        if gap <= 1:
            continue

        # Interpolate intermediate frames
        for g in range(1, gap):
            t = g / gap
            interp = tracks[f1] * (1 - t) + tracks[f2] * t
            interpolated[f1 + g] = interp

    interpolated[sorted_frames[-1]] = tracks[sorted_frames[-1]].copy()
    return interpolated


def _smooth_tracks(tracks, window=5):
    """Apply moving average smoothing to tracks."""
    smoothed = {}
    sorted_frames = sorted(tracks.keys())

    for i, frame_idx in enumerate(sorted_frames):
        start = max(0, i - window // 2)
        end = min(len(sorted_frames), i + window // 2 + 1)
        neighbor_frames = sorted_frames[start:end]

        # Average positions
        avg = np.zeros_like(tracks[frame_idx])
        count = np.zeros_like(tracks[frame_idx])

        for nf in neighbor_frames:
            valid = ~np.isnan(tracks[nf])
            avg[valid] += tracks[nf][valid]
            count[valid] += 1

        count[count == 0] = 1  # avoid div by zero
        smoothed[frame_idx] = avg / count

    return smoothed


def _anatomical_correction(tracks, point_names, limb_pairs, min_len, max_len):
    """Apply anatomical constraints to fix impossible positions."""
    corrected = {}
    name_to_idx = {name: i for i, name in enumerate(point_names)}

    for frame_idx, pts in tracks.items():
        fixed = pts.copy()

        # Check limb length ratios
        for upper, lower, parent_upper, parent_lower in limb_pairs:
            if all(n in name_to_idx for n in [upper, lower, parent_upper, parent_lower]):
                i_up = name_to_idx[upper]
                i_low = name_to_idx[lower]
                i_pup = name_to_idx[parent_upper]
                i_plow = name_to_idx[parent_lower]

                if all(not np.isnan(fixed[j, 0]) for j in [i_up, i_low, i_pup, i_plow]):
                    upper_len = np.linalg.norm(fixed[i_up] - fixed[i_pup])
                    lower_len = np.linalg.norm(fixed[i_low] - fixed[i_up])

                    # Flag unreasonable lengths
                    if lower_len > max_len or lower_len < min_len:
                        # Revert to parent position with small offset
                        fixed[i_low] = fixed[i_up] + (fixed[i_low] - fixed[i_up]) * 0.5

        corrected[frame_idx] = fixed

    return corrected


def _interpolate_missing_joints(landmarks, tracked_names):
    """Fill missing MediaPipe joints using symmetry from tracked points."""
    # Mirror pairs
    pairs = {
        (11, 12), (13, 14), (15, 16),  # arms
        (23, 24), (25, 26), (27, 28),  # legs
    }
    for left, right in pairs:
        if landmarks[left, 0] == 0 and landmarks[right, 0] != 0:
            landmarks[left] = landmarks[right]
            landmarks[left, 0] = 1.0 - landmarks[right, 0]  # mirror x
        elif landmarks[right, 0] == 0 and landmarks[left, 0] != 0:
            landmarks[right] = landmarks[left]
            landmarks[right, 0] = 1.0 - landmarks[left, 0]


@app.route("/extract", methods=["POST"])
def extract():
    """Start pose extraction with optional trim. Returns SSE event stream.

    POST body: {
        "video_path": "/abs/path/to/video.mp4",
        "pose_name": "walk",
        "skip_frames": 1,
        "start_time": 0.0,     // optional trim start
        "end_time": -1.0        // optional trim end (-1 = end of video)
    }
    """
    data = request.get_json(force=True)
    video_path = data.get("video_path", "")
    pose_name = data.get("pose_name", "pose")
    skip_frames = int(data.get("skip_frames", 1))
    start_time = float(data.get("start_time", 0))
    end_time = float(data.get("end_time", -1))

    if not video_path or not Path(video_path).exists():
        return jsonify({"error": f"Video not found: {video_path}"}), 400

    def generate():
        yield f"data: {json.dumps({'type': 'start', 'pose_name': pose_name})}\n\n"
        try:
            output_dir = str(_TMP_DIR / pose_name)
            for chunk in _extract_with_preview(
                video_path, output_dir, pose_name, skip_frames, start_time, end_time
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _extract_with_preview(
    video_path: str,
    output_dir: str,
    pose_name: str,
    skip_frames: int,
    start_time: float,
    end_time: float,
):
    """Core extraction pipeline with preview frames in SSE stream."""
    import cv2

    from agent.ml.keyframe_storage import KeyframeStorage as KFS
    from agent.ml.pose_detector import PoseDetector
    from agent.ml.pose_rotation import PoseRotationCalculator
    from agent.ml.pose_smoother import PoseSmoother
    from agent.ml.pose_validator import PoseValidator

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    # Apply trim
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps) if end_time > 0 else total_frames
    end_frame = min(end_frame, total_frames)

    detector = PoseDetector(static_image_mode=False)
    validator = PoseValidator()
    smoother = PoseSmoother()
    rotator = PoseRotationCalculator()
    rotator.set_auto_rest_pose()
    storage = KFS(base_path=Path(output_dir), name=pose_name, mode="w", fps=fps)

    # Seek to start
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    total_frames_trimmed = end_frame - start_frame
    processed = 0
    detected_frames = 0
    keyframes_stored = 0

    # Send skeleton config to frontend
    yield f"data: {json.dumps({'type': 'skeleton_config', 'bones': BONE_HIERARCHY})}\n\n"

    for frame_idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break

        processed += 1
        timestamp = frame_idx / fps

        # Progress every 20 frames
        if processed % 20 == 0 or processed == 1:
            pct = int(processed / total_frames_trimmed * 100)
            yield f"data: {json.dumps({'type': 'progress', 'frame': processed, 'total': total_frames_trimmed, 'pct': pct})}\n\n"

        # Detect pose
        result = detector.process_frame(frame)

        if not result or not result.get("body_landmarks"):
            storage.add_missing_frame(frame_id=frame_idx, timestamp=timestamp)
            continue

        landmarks_list = result["body_landmarks"].get("landmarks", [])
        if len(landmarks_list) != 33:
            storage.add_missing_frame(frame_id=frame_idx, timestamp=timestamp)
            continue

        landmarks = np.array(
            [[lm["x"], lm["y"], lm["z"]] for lm in landmarks_list],
            dtype=np.float32,
        )

        visibilities = np.array(
            [lm.get("visibility", 1.0) for lm in landmarks_list],
            dtype=np.float32,
        ) if "visibility" in landmarks_list[0] else None

        # Validate
        validation = validator.validate(landmarks, visibilities)
        if not validation.valid or validation.landmarks is None:
            storage.add_missing_frame(frame_id=frame_idx, timestamp=timestamp)
            continue

        detected_frames += 1
        smoothed, is_keyframe = smoother.smooth(validation.landmarks)

        if not is_keyframe:
            continue

        # Calculate rotations using rest pose delta
        rotations, confidences = rotator.calculate_with_confidence(smoothed, visibilities)

        storage.add_keyframe(
            frame_id=frame_idx,
            timestamp=timestamp,
            landmarks=smoothed,
            frame_type="key",
        )
        keyframes_stored += 1

        # Send preview frame every 10 keyframes
        if keyframes_stored % 10 == 0 or keyframes_stored == 1:
            preview_h, preview_w = 480, 640
            img_bytes = draw_skeleton_on_frame(frame, landmarks_list, preview_w, preview_h)
            if img_bytes:
                img_b64 = base64.b64encode(img_bytes).decode()
                yield f"data: {json.dumps({'type': 'preview', 'image': f'data:image/jpeg;base64,{img_b64}', 'frame': processed, 'keyframes': keyframes_stored, 'timestamp': timestamp})}\n\n"

    cap.release()
    storage.finalize()
    detector.close()

    result = {
        'type': 'done',
        'result': {
            'success': True,
            'total_frames': processed,
            'detected_frames': detected_frames,
            'keyframes_stored': keyframes_stored,
            'detection_rate': round(detected_frames / processed, 3) if processed > 0 else 0.0,
            'storage_path': output_dir,
            'pose_name': pose_name,
        }
    }
    yield f"data: {json.dumps(result)}\n\n"


@app.route("/poses")
def list_poses():
    poses = []
    if _TMP_DIR.exists():
        for d in sorted(_TMP_DIR.iterdir()):
            if d.is_dir():
                kf_file = d / f"{d.name}.keyframes.msgpack"
                if kf_file.exists():
                    stat = kf_file.stat()
                    poses.append({
                        "name": d.name,
                        "path": str(d),
                        "size_kb": round(stat.st_size / 1024, 1),
                    })
    return jsonify(poses)


@app.route("/pose/<name>")
def get_pose(name):
    pose_dir = _TMP_DIR / name
    storage = KeyframeStorage(base_path=pose_dir, name=name, mode="r")
    data = storage.to_json_serializable()
    storage.close()
    return jsonify(data)


@app.route("/save", methods=["POST"])
def save_pose():
    data = request.get_json(force=True)
    pose_name = data.get("pose_name", "")
    library_name = data.get("library_name", pose_name)

    src_dir = _TMP_DIR / pose_name
    if not src_dir.exists():
        return jsonify({"error": f"Pose not found: {pose_name}"}), 404

    dst_dir = _VROID_ANIMATIONS_DIR / library_name
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)

    logger.info(f"Saved pose {pose_name} -> {dst_dir}")
    return jsonify({"success": True, "path": str(dst_dir)})


if __name__ == "__main__":
    port = int(os.environ.get("POSE_EXTRACTOR_PORT", 5001))
    logger.info(f"Pose Extractor starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
