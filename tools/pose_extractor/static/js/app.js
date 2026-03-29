/**
 * Pose Extractor - Frontend app
 * Video trimmer + skeleton overlay + Three.js VRM preview
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// State
let scene, camera, renderer, controls;
let currentVrm = null;
let poseData = null;
let isPlaying = false;
let currentFrameIndex = 0;
let playbackTime = 0;
const clock = new THREE.Clock();

// Video state
let videoInfo = null;
let trimStart = 0;
let trimEnd = 0;

// Manual setup state
let manualMode = false;
let placedPoints = {};  // {name: [x, y]} in display coords
let displaySize = {w: 640, h: 480};
const POINT_NAMES = [
  'left_shoulder', 'right_shoulder',
  'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist',
  'left_hip', 'right_hip',
  'left_knee', 'right_knee',
  'left_ankle', 'right_ankle',
];
let currentPointIndex = 0;

// Canvas references
const vrmCanvas = document.getElementById('vrm-canvas');  // Three.js WebGL
const previewCanvas = document.getElementById('preview-canvas');  // 2D skeleton overlay
const previewCtx = previewCanvas.getContext('2d');
let lastLandmarks = [];

// Skeleton connections
const SKELETON = [
  [11,13],[13,15],[12,14],[14,16],
  [11,12],[23,24],
  [23,25],[25,27],[24,26],[26,28],
  [11,23],[12,24],[0,11],[0,12],
];

const BONE_NAMES = [
  'Hips','Spine','Chest','UpperChest','LeftShoulder','LeftUpperArm','LeftLowerArm',
  'RightShoulder','RightUpperArm','RightLowerArm','LeftUpperLeg','LeftLowerLeg',
  'RightUpperLeg','RightLowerLeg','Head'
];

const BONE_ALIASES = {
  'leftupperarm': ['leftarm','left_upper_arm'],
  'leftlowerarm': ['leftforearm','left_lower_arm'],
  'rightupperarm': ['rightarm','right_upper_arm'],
  'rightlowerarm': ['rightforearm','right_lower_arm'],
  'leftupperleg': ['leftupleg','leftupperleg'],
  'leftlowerleg': ['leftleg','left_lower_leg'],
  'rightupperleg': ['rightupleg','rightupperleg'],
  'rightlowerleg': ['rightleg','right_lower_leg'],
  'chest': ['spine1','chest'],
  'hips': ['root','hips'],
  'neck': ['neck'],
  'head': ['head'],
  'leftshoulder': ['leftshoulder'],
  'rightshoulder': ['rightshoulder'],
};

// Init Three.js on vrm-canvas
function init() {
  const container = document.getElementById('preview-container');
  const w = container.clientWidth;
  const h = container.clientHeight;

  vrmCanvas.width = w;
  vrmCanvas.height = h;
  previewCanvas.width = w;
  previewCanvas.height = h;

  renderer = new THREE.WebGLRenderer({ canvas: vrmCanvas, antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x111111);

  camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
  camera.position.set(0, 1, 3);

  controls = new OrbitControls(camera, vrmCanvas);
  controls.target.set(0, 1, 0);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.0));
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
  dirLight.position.set(2, 4, 2);
  scene.add(dirLight);
  scene.add(new THREE.GridHelper(4, 8, 0x333333, 0x222222));

  window.addEventListener('resize', () => {
    const cw = container.clientWidth;
    const ch = container.clientHeight;
    camera.aspect = cw / ch;
    camera.updateProjectionMatrix();
    renderer.setSize(cw, ch);
    vrmCanvas.width = cw;
    vrmCanvas.height = ch;
    previewCanvas.width = cw;
    previewCanvas.height = ch;
  });

  // Start with preview canvas visible, VRM canvas behind
  previewCanvas.style.display = 'block';

  animate();
}

function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();

  if (isPlaying && poseData && currentVrm) {
    playbackTime += delta;
    const keyframes = poseData.keyframes;

    let found = false;
    for (let i = 0; i < keyframes.length; i++) {
      if (keyframes[i].timestamp >= playbackTime) {
        currentFrameIndex = i;
        found = true;
        break;
      }
    }
    if (!found) {
      playbackTime = 0;
      currentFrameIndex = 0;
    }

    applyKeyframe(keyframes[currentFrameIndex]);
    updateFrameDisplay();
  }

  controls.update();
  renderer.render(scene, camera);
}

// Skeleton overlay on preview canvas
function drawSkeletonOverlay(landmarks, w, h) {
  previewCtx.save();
  previewCtx.strokeStyle = '#00ff00';
  previewCtx.lineWidth = 2;

  SKELETON.forEach(([a, b]) => {
    if (a < landmarks.length && b < landmarks.length) {
      previewCtx.beginPath();
      previewCtx.moveTo(landmarks[a].x * w, landmarks[a].y * h);
      previewCtx.lineTo(landmarks[b].x * w, landmarks[b].y * h);
      previewCtx.stroke();
    }
  });

  previewCtx.fillStyle = '#00ff00';
  landmarks.forEach((lm, i) => {
    previewCtx.beginPath();
    previewCtx.arc(lm.x * w, lm.y * h, 4, 0, Math.PI * 2);
    previewCtx.fill();
  });
  previewCtx.restore();
}

function updateFrameDisplay() {
  document.getElementById('status-frame').textContent = `Frame: ${currentFrameIndex}`;
  document.getElementById('status-keyframes').textContent = `Keyframes: ${poseData?.keyframes?.length || 0}`;
}

// VRM loading
function findBone(boneMap, name) {
  if (!boneMap) return null;
  const lower = name.toLowerCase();
  if (boneMap[lower]) return boneMap[lower];
  for (const alias of (BONE_ALIASES[lower] || [])) {
    if (boneMap[alias]) return boneMap[alias];
  }
  return null;
}

function collectBones(scene) {
  const bones = {};
  scene.traverse(child => {
    if (child.isBone) bones[child.name.toLowerCase()] = child;
  });
  return bones;
}

async function loadVrm(url) {
  if (currentVrm) {
    scene.remove(currentVrm.scene);
    currentVrm = null;
  }

  // Show VRM canvas, hide 2D preview
  previewCanvas.style.display = 'none';

  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.load(url, async (gltf) => {
      if (gltf.userData?.vrm) {
        currentVrm = gltf.userData.vrm;
        scene.add(currentVrm.scene);
        logInfo(`Loaded VRM: ${url}`);
      } else {
        try {
          const { VRM } = await import('@pixiv/three-vrm');
          const vrm = await VRM.from(gltf);
          currentVrm = vrm;
          scene.add(vrm.scene);
          logInfo(`Loaded VRM (three-vrm): ${url}`);
        } catch {
          currentVrm = { scene: gltf.scene, humanoid: null, bones: collectBones(gltf.scene) };
          scene.add(gltf.scene);
          logInfo(`Loaded GLTF fallback: ${url}`);
        }
      }
      resolve();
    }, undefined, reject);
  });
}

function applyKeyframe(keyframe) {
  if (!currentVrm || !keyframe?.bones) return;
  const boneNames = poseData?.bone_names || BONE_NAMES;

  keyframe.bones.forEach((quat, i) => {
    if (i >= boneNames.length) return;
    const name = boneNames[i];
    if (!name) return;

    let bone = null;
    if (currentVrm.humanoid) {
      bone = currentVrm.humanoid.getBoneNode(name);
    } else if (currentVrm.bones) {
      bone = findBone(currentVrm.bones, name);
    }
    if (bone) {
      bone.quaternion.set(quat[0], quat[1], quat[2], quat[3]);
    }
  });
}

// API calls
async function loadVideoInfo() {
  const videoPath = document.getElementById('video-path').value.trim();
  if (!videoPath) return logError('Enter a video path');

  logInfo('Loading video info...');
  try {
    const res = await fetch('/video-info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_path: videoPath })
    });
    const data = await res.json();
    if (data.error) return logError(data.error);

    videoInfo = data;
    trimStart = 0;
    trimEnd = data.duration;

    document.getElementById('trim-start').value = 0;
    document.getElementById('trim-end').value = data.duration;
    document.getElementById('video-duration').textContent = `${data.duration.toFixed(1)}s`;
    document.getElementById('trimmer').style.display = 'block';
    document.getElementById('btn-extract').disabled = false;
    document.getElementById('manual-setup').style.display = 'block';

    logInfo(`Video: ${data.duration.toFixed(1)}s, ${data.fps}fps, ${data.total_frames} frames`);
    updateTimeline();
  } catch (err) {
    logError(`Failed: ${err.message}`);
  }
}

// Manual skeleton setup
async function setupManualMode() {
  const videoPath = document.getElementById('video-path').value.trim();
  if (!videoPath) return logError('Load video first');

  try {
    const res = await fetch('/first-frame', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_path: videoPath, timestamp: trimStart })
    });
    const data = await res.json();
    if (data.error) return logError(data.error);

    // Store display dimensions
    displaySize = { w: data.width, h: data.height };

    // Show frame on preview canvas
    previewCanvas.style.display = 'block';
    previewCanvas.style.zIndex = '2';

    const img = new Image();
    img.onload = () => {
      previewCanvas.width = data.width;
      previewCanvas.height = data.height;
      previewCtx.drawImage(img, 0, 0);

      // Enable manual mode
      manualMode = true;
      placedPoints = {};
      currentPointIndex = 0;

      document.getElementById('btn-manual-setup').style.display = 'none';
      document.getElementById('btn-clear-points').style.display = 'inline-block';
      document.getElementById('btn-track').style.display = 'none';

      updatePointStatus();
      logInfo('Click on the video to place skeleton points');
    };
    img.src = data.image;
  } catch (err) {
    logError(`Setup failed: ${err.message}`);
  }
}

function handleCanvasClick(e) {
  if (!manualMode) return;

  const rect = previewCanvas.getBoundingClientRect();
  // Scale from CSS coordinates to canvas pixel coordinates
  const scaleX = previewCanvas.width / rect.width;
  const scaleY = previewCanvas.height / rect.height;
  const x = (e.clientX - rect.left) * scaleX;
  const y = (e.clientY - rect.top) * scaleY;

  if (currentPointIndex >= POINT_NAMES.length) return;

  const pointName = POINT_NAMES[currentPointIndex];
  placedPoints[pointName] = [x, y];
  currentPointIndex++;

  // Draw point (use canvas coordinates)
  previewCtx.fillStyle = '#ff0';
  previewCtx.beginPath();
  previewCtx.arc(x, y, 6, 0, Math.PI * 2);
  previewCtx.fill();

  // Draw label
  previewCtx.fillStyle = '#fff';
  previewCtx.font = '10px monospace';
  previewCtx.fillText(pointName, x + 8, y - 4);

  updatePointStatus();
  drawPlacedSkeleton();
}

function drawPlacedSkeleton() {
  // Redraw connections between placed points
  const connections = [
    ['left_shoulder', 'left_elbow'], ['left_elbow', 'left_wrist'],
    ['right_shoulder', 'right_elbow'], ['right_elbow', 'right_wrist'],
    ['left_shoulder', 'right_shoulder'],
    ['left_hip', 'right_hip'],
    ['left_shoulder', 'left_hip'], ['right_shoulder', 'right_hip'],
    ['left_hip', 'left_knee'], ['left_knee', 'left_ankle'],
    ['right_hip', 'right_knee'], ['right_knee', 'right_ankle'],
  ];

  previewCtx.strokeStyle = '#0f0';
  previewCtx.lineWidth = 2;

  connections.forEach(([a, b]) => {
    if (placedPoints[a] && placedPoints[b]) {
      previewCtx.beginPath();
      previewCtx.moveTo(placedPoints[a][0], placedPoints[a][1]);
      previewCtx.lineTo(placedPoints[b][0], placedPoints[b][1]);
      previewCtx.stroke();
    }
  });
}

function updatePointStatus() {
  const total = POINT_NAMES.length;
  const placed = Object.keys(placedPoints).length;
  document.getElementById('point-status').textContent = `${placed}/${total} points placed`;

  // Update point list
  const list = document.getElementById('point-list');
  list.innerHTML = POINT_NAMES.map((name, i) => {
    const placed = placedPoints[name] ? '✓' : '○';
    const current = i === currentPointIndex ? '→ ' : '  ';
    return `<div>${current}${placed} ${name.replace(/_/g, ' ')}</div>`;
  }).join('');

  // Show track button when enough points placed
  if (placed >= 6) {
    document.getElementById('btn-track').style.display = 'inline-block';
  }
}

function clearPoints() {
  if (!videoInfo) return;

  placedPoints = {};
  currentPointIndex = 0;

  // Redraw frame
  const videoPath = document.getElementById('video-path').value.trim();
  fetch('/first-frame', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_path: videoPath, timestamp: trimStart })
  })
    .then(r => r.json())
    .then(data => {
      const img = new Image();
      img.onload = () => {
        previewCtx.drawImage(img, 0, 0);
      };
      img.src = data.image;
    });

  updatePointStatus();
  document.getElementById('btn-track').style.display = 'none';
}

async function startTracking() {
  const videoPath = document.getElementById('video-path').value.trim();
  const poseName = document.getElementById('pose-name').value.trim() || 'tracked';

  if (Object.keys(placedPoints).length < 6) return logError('Place at least 6 points');

  logInfo('Starting tracking...');
  document.getElementById('btn-track').disabled = true;

  try {
    const res = await fetch('/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: videoPath,
        pose_name: poseName,
        points: placedPoints,
        display_width: displaySize.w,
        display_height: displaySize.h,
        start_time: trimStart,
        end_time: trimEnd,
      })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      for (const line of text.split('\n').filter(l => l.startsWith('data:'))) {
        try {
          handleSseEvent(JSON.parse(line.substring(5).trim()));
        } catch {}
      }
    }
  } catch (err) {
    logError(`Tracking failed: ${err.message}`);
  } finally {
    document.getElementById('btn-track').disabled = false;
    refreshPoses();
  }
}

async function previewFrame() {
  const videoPath = document.getElementById('video-path').value.trim();
  const timestamp = parseFloat(document.getElementById('trim-start').value) || 0;

  try {
    const res = await fetch('/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_path: videoPath, timestamp })
    });
    const data = await res.json();
    if (data.error) return logError(data.error);

    if (data.image) {
      // Show 2D preview canvas, hide VRM canvas
      previewCanvas.style.display = 'block';
      previewCanvas.style.zIndex = '2';

      const img = new Image();
      img.onload = () => {
        previewCanvas.width = previewCanvas.clientWidth;
        previewCanvas.height = previewCanvas.clientHeight;
        previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);

        // Draw skeleton overlay
        if (data.landmarks) {
          drawSkeletonOverlay(data.landmarks, previewCanvas.width, previewCanvas.height);
        }
      };
      img.src = data.image;
    }

    document.getElementById('preview-info').textContent = `Frame at ${timestamp.toFixed(2)}s`;
    logInfo(`Preview: ${timestamp.toFixed(2)}s, frame ${data.frame}`);
  } catch (err) {
    logError(`Preview failed: ${err.message}`);
  }
}

async function startExtraction() {
  const videoPath = document.getElementById('video-path').value.trim();
  const poseName = document.getElementById('pose-name').value.trim() || 'pose';
  const skipFrames = parseInt(document.getElementById('skip-frames').value, 10);

  if (!videoPath) return logError('Enter a video path');

  logInfo(`Starting extraction: ${videoPath}`);
  document.getElementById('btn-extract').disabled = true;

  try {
    const res = await fetch('/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_path: videoPath,
        pose_name: poseName,
        skip_frames: skipFrames,
        start_time: trimStart,
        end_time: trimEnd,
      })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      for (const line of text.split('\n').filter(l => l.startsWith('data:'))) {
        try {
          handleSseEvent(JSON.parse(line.substring(5).trim()));
        } catch {}
      }
    }
  } catch (err) {
    logError(`Extraction failed: ${err.message}`);
  } finally {
    document.getElementById('btn-extract').disabled = false;
    refreshPoses();
  }
}

function handleSseEvent(event) {
  switch (event.type) {
    case 'start':
      logInfo(`Extracting: ${event.pose_name}`);
      break;
    case 'status':
      logInfo(`[STATUS] ${event.message}`);
      break;
    case 'progress':
      logInfo(`Frame ${event.frame}/${event.total} (${event.pct}%)`);
      document.getElementById('status-detection').textContent = `Progress: ${event.pct}%`;
      break;
    case 'frame':
      // Real-time frame preview during tracking
      if (event.image) {
        previewCanvas.style.display = 'block';
        previewCanvas.style.zIndex = '2';
        const img = new Image();
        img.onload = () => {
          previewCanvas.width = previewCanvas.clientWidth;
          previewCanvas.height = previewCanvas.clientHeight;
          previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);

          // Keyframe indicator
          if (event.is_keyframe) {
            previewCtx.fillStyle = '#0f0';
            previewCtx.font = 'bold 16px monospace';
            previewCtx.fillText('KEYFRAME', 10, 25);
          } else {
            previewCtx.fillStyle = '#888';
            previewCtx.font = '12px monospace';
            previewCtx.fillText('interpolating...', 10, 25);
          }
        };
        img.src = event.image;
      }
      document.getElementById('status-frame').textContent = `Frame: ${event.frame}/${event.total}`;
      document.getElementById('status-keyframes').textContent = `Keyframes: ${event.keyframes}`;
      document.getElementById('status-detection').textContent = `Tracked: ${event.tracked} pts`;
      break;
    case 'preview':
      // Legacy preview event
      if (event.image) {
        previewCanvas.style.display = 'block';
        previewCanvas.style.zIndex = '2';
        const img = new Image();
        img.onload = () => {
          previewCanvas.width = previewCanvas.clientWidth;
          previewCanvas.height = previewCanvas.clientHeight;
          previewCtx.drawImage(img, 0, 0, previewCanvas.width, previewCanvas.height);
        };
        img.src = event.image;
      }
      document.getElementById('status-frame').textContent = `Extracting: ${event.frame}`;
      document.getElementById('status-keyframes').textContent = `Keyframes: ${event.keyframes}`;
      break;
    case 'done':
      logInfo(`Done! ${event.result.keyframes_stored} keyframes stored`);
      logInfo(`Pose saved as: ${event.result.pose_name}`);

      // Auto-select the new pose in dropdown
      const poseSelect = document.getElementById('pose-select');
      const newOption = document.createElement('option');
      newOption.value = event.result.pose_name;
      newOption.textContent = event.result.pose_name;
      poseSelect.prepend(newOption);
      poseSelect.value = event.result.pose_name;
      document.getElementById('library-name').value = event.result.pose_name;

      logInfo('Click "Load Pose" to preview on VRM model');
      break;
    case 'error':
      logError(event.message);
      break;
  }
}

async function refreshModels() {
  const res = await fetch('/models');
  const data = await res.json();
  document.getElementById('vrm-select').innerHTML = data.vrms.map(v => `<option value="${v}">${v}</option>`).join('');
  if (data.vrms.length > 0) loadVrm(`/vrm/${data.vrms[0]}`);
  await refreshPoses();
}

async function refreshPoses() {
  const res = await fetch('/poses');
  const poses = await res.json();
  document.getElementById('pose-select').innerHTML = poses.map(p => `<option value="${p.name}">${p.name} (${p.size_kb}KB)</option>`).join('');

  const modelsRes = await fetch('/models');
  const modelsData = await modelsRes.json();
  document.getElementById('saved-list').innerHTML = modelsData.poses.map(p => `<div class="saved-item">${p}</div>`).join('');
}

async function loadPose() {
  const name = document.getElementById('pose-select').value;
  if (!name) return;
  logInfo(`Loading pose: ${name}`);
  const res = await fetch(`/pose/${name}`);
  poseData = await res.json();
  currentFrameIndex = 0;
  playbackTime = 0;
  updateFrameDisplay();

  // Hide 2D preview, show VRM canvas
  previewCanvas.style.display = 'none';
  previewCanvas.style.zIndex = '1';

  if (currentVrm) {
    logInfo(`Loaded ${poseData.total_keyframes} keyframes — press Play to animate`);
    // Apply first frame immediately
    if (poseData.keyframes && poseData.keyframes.length > 0) {
      applyKeyframe(poseData.keyframes[0]);
    }
  } else {
    logInfo(`Loaded ${poseData.total_keyframes} keyframes — load VRM model first, then press Play`);
  }
}

async function saveToLibrary() {
  const poseName = document.getElementById('pose-select').value;
  const libraryName = document.getElementById('library-name').value.trim() || poseName;
  if (!poseName) return;
  const res = await fetch('/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pose_name: poseName, library_name: libraryName })
  });
  const data = await res.json();
  if (data.success) logInfo(`Saved: ${data.path}`);
  else logError(data.error || 'Save failed');
  refreshPoses();
}

// Timeline trimmer
function updateTimeline() {
  if (!videoInfo) return;
  const dur = videoInfo.duration;
  const startPct = (trimStart / dur) * 100;
  const endPct = (trimEnd / dur) * 100;

  document.getElementById('timeline-bar').style.left = `${startPct}%`;
  document.getElementById('timeline-bar').style.width = `${endPct - startPct}%`;
  document.getElementById('handle-start').style.left = `${startPct}%`;
  document.getElementById('handle-end').style.left = `${endPct}%`;
  document.getElementById('trim-start').value = trimStart.toFixed(1);
  document.getElementById('trim-end').value = trimEnd.toFixed(1);
}

function setupTimelineDrag() {
  const timeline = document.getElementById('timeline');

  timeline.addEventListener('click', (e) => {
    if (!videoInfo) return;
    const rect = timeline.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const time = pct * videoInfo.duration;

    // Preview at this time
    document.getElementById('trim-start').value = time.toFixed(1);
    trimStart = time;
    updateTimeline();
    previewFrame();
  });
}

// Logging
function logInfo(msg) { appendLog(msg, 'log-info'); }
function logError(msg) { appendLog(msg, 'log-error'); }
function logWarn(msg) { appendLog(msg, 'log-warn'); }
function appendLog(msg, cls) {
  const log = document.getElementById('progress-log');
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// Event bindings
document.addEventListener('DOMContentLoaded', () => {
  init();
  refreshModels();
  setupTimelineDrag();

  document.getElementById('btn-load-video').addEventListener('click', loadVideoInfo);
  document.getElementById('btn-preview-frame').addEventListener('click', previewFrame);
  document.getElementById('btn-extract').addEventListener('click', startExtraction);
  document.getElementById('btn-load-pose').addEventListener('click', loadPose);
  document.getElementById('btn-save').addEventListener('click', saveToLibrary);

  // Manual setup
  document.getElementById('btn-manual-setup').addEventListener('click', setupManualMode);
  document.getElementById('btn-clear-points').addEventListener('click', clearPoints);
  document.getElementById('btn-track').addEventListener('click', startTracking);
  previewCanvas.addEventListener('click', handleCanvasClick);

  document.getElementById('btn-play').addEventListener('click', () => { isPlaying = true; });
  document.getElementById('btn-pause').addEventListener('click', () => { isPlaying = false; });
  document.getElementById('btn-stop').addEventListener('click', () => {
    isPlaying = false;
    currentFrameIndex = 0;
    playbackTime = 0;
    updateFrameDisplay();
  });

  document.getElementById('vrm-select').addEventListener('change', (e) => {
    loadVrm(`/vrm/${e.target.value}`);
  });
  document.getElementById('btn-load-vrm').addEventListener('click', () => {
    const path = document.getElementById('vrm-path').value.trim();
    if (path) loadVrm(`/vrm-at-path?path=${encodeURIComponent(path)}`);
  });

  document.getElementById('trim-start').addEventListener('change', (e) => {
    trimStart = parseFloat(e.target.value) || 0;
    updateTimeline();
  });
  document.getElementById('trim-end').addEventListener('change', (e) => {
    trimEnd = parseFloat(e.target.value) || 0;
    updateTimeline();
  });

  document.getElementById('pose-select').addEventListener('change', (e) => {
    document.getElementById('library-name').value = e.target.value;
  });
});
