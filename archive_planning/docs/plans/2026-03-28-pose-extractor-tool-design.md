# Pose Extractor Tool — Design Document

**Date**: 2026-03-28  
**Status**: Approved  
**Scope**: `tools/pose_extractor/` — standalone local tool, completely separate from main Mimi agent server

---

## 1. Context

The Mimi project has an existing ML pose pipeline in `agent/ml/`:
- `PoseExtractor` — orchestrates the full pipeline
- `VideoExtractor` — extracts frames from video via FFmpeg
- `PoseDetector` — detects body/hand/face landmarks via MediaPipe Tasks
- `SkeletonStorage` — stores pose frames as `.msgpack` + JSON index files

The goal is a developer tool to:
1. Extract poses from reference videos
2. Preview extracted poses on a VRM model in the browser
3. Save approved pose sequences to `vroid_model/animations/` as the project's animation library

This tool is entirely separate from the main agent system (different port, no shared process), runs locally, no Docker.

---

## 2. Approach

**Flask monolítico** — single Python server (`python server.py`) that:
- Serves the static frontend (HTML + vanilla JS)
- Exposes a REST API for extraction, preview data, and saving
- Streams extraction progress via SSE (Server-Sent Events)
- Runs on port 5001 (avoids conflicts with main agent on 8765/5173)

---

## 3. Directory Structure

```
tools/pose_extractor/
├── server.py               # Flask app — single entry point
├── extract.py              # Optional standalone CLI
├── requirements.txt        # Flask + project deps
├── tmp/                    # Temp extracted pose files (gitignored)
└── static/
    ├── index.html          # Single-page app
    └── js/
        └── app.js          # Three.js + three-vrm + UI logic
```

Output library: `vroid_model/animations/<name>/`  
Available VRM models: `vroid_model/Mimi.vrm`, `vroid_model/Mimi01.vrm`, `vroid_model/Nazuna.vrm`

---

## 4. Backend API

| Endpoint | Method | Body | Response | Description |
|---|---|---|---|---|
| `/` | GET | — | HTML | Serves `index.html` |
| `/static/<path>` | GET | — | file | Serves JS/CSS |
| `/models` | GET | — | `{vrms: [...], poses: [...]}` | Lists available VRM files and saved poses |
| `/extract` | POST | `{video_path, pose_name, skip_frames}` | SSE stream | Runs pipeline, streams progress events |
| `/poses` | GET | — | `[{name, path, frames, fps, duration}]` | Lists extracted poses in `tmp/` |
| `/pose/<name>` | GET | — | `{frames: [...]}` | Returns pose frame data for preview |
| `/save` | POST | `{pose_name, library_name}` | `{success, path}` | Copies pose files to `vroid_model/animations/<name>/` |

### SSE Event Format (for `/extract`)

```
data: {"type": "progress", "frame": 42, "total": 300, "pct": 14}
data: {"type": "done", "result": {"total_frames": 300, "detected_frames": 287, "detection_rate": 0.957}}
data: {"type": "error", "message": "..."}
```

---

## 5. Frontend Layout

Single HTML page with three vertical panels:

**Panel 1 — Extract**
- Video file path input (text field, local filesystem path)
- Pose name input
- Skip frames selector (1 = all frames, 2 = every other, etc.)
- Extract button
- Live progress log (SSE stream, scrollable)
- Detection rate summary on completion

**Panel 2 — Preview**
- Three.js canvas with VRM model loaded
- VRM selector dropdown (populated from `/models`)
- Extracted pose selector dropdown (populated from `/poses`)
- Play / Pause / Stop controls
- Frame scrubber (range input)
- FPS display

**Panel 3 — Save to Library**
- Library name input (defaults to pose_name)
- Save button (`POST /save`)
- Confirmation message with saved path
- List of currently saved library poses (from `/models`)

---

## 6. Pose Playback in Browser

The frontend fetches pose frame data (`/pose/<name>`) after extraction. Each frame contains `body_pose` (33 landmarks x 3 coords), `left_hand`, `right_hand`, `face`.

Bone mapping (MediaPipe landmarks → VRM humanoid bones) is implemented inline in `app.js` using the same mapping logic from `web_avatar/src/logic/PosePlayer.js`. Landmark positions are converted to bone rotations (quaternions) using vector cross products and applied to the loaded VRM skeleton each animation frame.

Three.js and three-vrm are loaded from CDN (no bundler needed):
```html
<script type="importmap">
  { "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.168.0/build/three.module.js",
    "@pixiv/three-vrm": "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@3/lib/three-vrm.module.js"
  }}
</script>
```

---

## 7. Data Flow

```
[User enters video path + pose name]
  → POST /extract
  → Flask spawns extraction in background thread
  → VideoExtractor iterates frames
  → PoseDetector processes each frame (MediaPipe)
  → SkeletonStorage writes to tools/pose_extractor/tmp/<pose_name>/
  → SSE progress events → browser progress log

[User clicks pose in selector]
  → GET /pose/<name>
  → Flask reads tmp/<name>/<name>.msgpack
  → Returns frame data as JSON
  → app.js maps landmarks to VRM bones
  → Three.js renders pose on VRM in canvas

[User clicks Save]
  → POST /save {pose_name, library_name}
  → Flask copies tmp/<pose_name>/ to vroid_model/animations/<library_name>/
  → Returns success + path
```

---

## 8. Python Import Strategy

`server.py` adds the project root to `sys.path` before importing `agent/ml/`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agent.ml.pose_extractor import PoseExtractor
```

This avoids duplicating any ML code and keeps the tool thin.

---

## 9. Requirements

`tools/pose_extractor/requirements.txt`:
```
flask>=3.0.0
flask-cors>=4.0.0
# agent/ml deps (also in root requirements.txt):
mediapipe>=0.10.0
opencv-python>=4.8.0
msgpack>=1.0.0
numpy>=1.24.0
```

To run:
```bash
cd /path/to/mimi
source .venv/bin/activate
python tools/pose_extractor/server.py
# open http://localhost:5001
```

---

## 10. Refined Extraction Algorithm (Approved 2026-03-28)

### 10.1 Keyframing Strategy

Frame-by-frame during extraction:
1. Detect pose in frame (MediaPipe)
2. Validate pose (confidence, anatomical plausibility)
3. Compare with previous frame:
   - Small change → interpolatable, mark as "intermediate" (not stored)
   - Large change → mark as "keyframe" (stored)
   - Detection failure → mark as "missing" (interpolated from neighbors)
4. Store only keyframes + Bezier tangents
5. Playback interpolates between keyframes automatically

Expected result: ~60-80% data reduction vs storing every frame.

### 10.2 Validation Pipeline (4 stages)

Every frame passes through all 4 stages:

**Stage 1 — Confidence Check**
- MediaPipe returns visibility/confidence per landmark (0.0–1.0)
- Minimum threshold: 0.5 for main body landmarks
- If <60% of landmarks pass → discard frame entirely

**Stage 2 — Anatomical Validation**
- Adjacent joint distances must be proportional (shoulder-elbow ≈ elbow-wrist)
- Detects impossibilities: arm through torso, inverted knee, etc.
- Uses anatomical ratios (not absolute values — camera-distance independent)

**Stage 3 — Temporal Coherence**
- Compare with last valid keyframe
- Max velocity per joint (prevents landmark "teleporting")
- If a joint moves >threshold between consecutive frames → discard that joint only (not the whole frame)
- Discarded joints interpolated from surrounding keyframes

**Stage 4 — Outlier Rejection**
- Compute rolling mean of last N keyframes per joint
- If joint deviates >2σ from mean → mark as outlier
- Outliers replaced by interpolation

### 10.3 Smoothing

Two layers applied before keyframe decision:

**Layer 1 — Spatial Smoothing (per frame)**
- Gaussian blur over landmarks per frame
- Small kernel (σ=1.5) — removes noise without distorting real position
- Applied per joint individually

**Layer 2 — Temporal Smoothing (between keyframes)**
- Exponential Moving Average (EMA) with α=0.7
- α=0.7: follows real movement, avoids lag
- Applied after spatial smoothing

**Keyframe Interpolation**
- Cubic Bezier (not linear) between keyframe A and B
- Natural acceleration/deceleration (ease-in/ease-out)
- Tangents auto-calculated from neighboring keyframes (Catmull-Rom)

### 10.4 Storage Format

New `.msgpack` structure (replaces old per-frame flat list):

```
header:
  fps: float
  duration: float
  total_keyframes: int
  format_version: 2

keyframes: [
  {
    frame_id: int,
    timestamp: float16,         # half-precision (vs float32)
    type: "key" | "missing",
    body: [13 joints × 4],      # quaternions (xyzw), not XYZ coords
    hands: {left, right},       # omitted if not detected
    face: null | [6 points],    # 6 key landmarks only (not 468)
  }
]

bezier_tangents: [...]          # pre-calculated Catmull-Rom tangents
```

**Estimated gains vs current format:**
- float16 vs float32: 50% size reduction
- Quaternions: rotations ready for VRM (no conversion at playback)
- Keyframes only: 60-80% fewer entries
- Face: 6 points vs 468 (98% reduction)
- Hands omitted when absent
- Result: ~2-5 MB per minute of video (vs ~50 MB current)

---

## 11. Out of Scope

- Authentication / multi-user
- Real-time video capture (camera input)
- Docker support
- Integration with main agent EventBus
- Deploying to any server
