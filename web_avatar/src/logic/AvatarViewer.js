/**
 * AvatarViewer - Three.js scene manager for VRM models
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { AnimationManager } from './AnimationManager';
import { ExpressionController } from './ExpressionController';

export class AvatarViewer {
    constructor(canvas, wsConnection = null) {
        this.canvas = canvas;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.vrm = null;
        this.animationManager = null;
        this.expressionController = null;
        this.clock = new THREE.Clock();
        this.animationId = null;
        this.onCameraChange = null;

        this.wsConnection = wsConnection;
        this.frameCapture = {
            enabled: false,
            interval: 100,
            lastCaptureTime: 0,
            frameCount: 0
        };

        this.init();
    }

    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            45,
            this.canvas.clientWidth / this.canvas.clientHeight,
            0.1,
            100
        );
        this.camera.position.set(0, 1.4, 2);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        // Lights
        this.setupLights();

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.target.set(0, 1.2, 0);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 0.5;
        this.controls.maxDistance = 10;

        // Broadcast camera changes
        this.controls.addEventListener('change', () => {
            if (this.onCameraChange) {
                this.onCameraChange({
                    position: this.camera.position,
                    target: this.controls.target
                });
            }
        });

        this.controls.update();

        // Handle window resize (should be handled by React resize observer usually, but manual binding is ok for now)
        // window.addEventListener('resize', () => this.onWindowResize());

        // Start animation loop
        this.animate();
    }

    setupLights() {
        // Ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        // Directional light (main)
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
        directionalLight.position.set(1, 2, 1);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 10;
        this.scene.add(directionalLight);

        // Fill light (softer, from the side)
        const fillLight = new THREE.DirectionalLight(0x8888ff, 0.4);
        fillLight.position.set(-1, 1, -1);
        this.scene.add(fillLight);

        // Rim light (back light for depth)
        const rimLight = new THREE.DirectionalLight(0xffffff, 0.3);
        rimLight.position.set(0, 1, -2);
        this.scene.add(rimLight);

        // Optional: Add hemisphere light for more natural lighting
        const hemisphereLight = new THREE.HemisphereLight(0x8888ff, 0x444444, 0.3);
        this.scene.add(hemisphereLight);
    }

    async loadVRM(url) {
        // Prevent concurrent loads
        if (this.isLoading) {
            console.warn('VRM Loading in progress, ignoring request:', url);
            return Promise.reject(new Error('Loading in progress'));
        }
        this.isLoading = true;

        // Remove existing VRM if any
        if (this.vrm) {
            this.scene.remove(this.vrm.scene);
            VRMUtils.deepDispose(this.vrm.scene);
            this.vrm = null;
        }

        // Clean up previous managers
        if (this.animationManager) {
            this.animationManager.dispose();
            this.animationManager = null;
        }
        if (this.expressionController) {
            this.expressionController.dispose();
            this.expressionController = null;
        }

        return new Promise((resolve, reject) => {
            const loader = new GLTFLoader();

            // Register VRM plugin
            loader.register((parser) => {
                return new VRMLoaderPlugin(parser);
            });

            loader.load(
                url,
                (gltf) => {
                    this.isLoading = false;
                    // Retrieve VRM instance
                    const vrm = gltf.userData.vrm;
                    this.vrm = vrm; // Store immediately

                    if (!vrm) {
                        reject(new Error('VRM data not found in loaded model'));
                        return;
                    }

                    this.vrm = vrm;

                    // Disable frustum culling for VRM
                    vrm.scene.traverse((obj) => {
                        obj.frustumCulled = false;
                    });

                    // Add to scene
                    this.scene.add(vrm.scene);

                    // Rotate model to face camera using humanoid hips
                    // VRM models are typically facing +Z, we want them facing -Z (camera)
                    if (vrm.humanoid) {
                        const hips = vrm.humanoid.getNormalizedBoneNode('hips');
                        if (hips) {
                            hips.rotation.y = Math.PI; // 180 degrees
                        }
                    }

                    // Initialize Animation Manager
                    this.animationManager = new AnimationManager(vrm);

                    // Initialize Expression Controller
                    this.expressionController = new ExpressionController(vrm);

                    console.log('VRM loaded successfully:', vrm);
                    resolve(vrm);
                },
                (progress) => {
                    // console.log(`Loading model: ${(progress.loaded / progress.total * 100).toFixed(1)}%`);
                },
                (error) => {
                    this.isLoading = false;
                    console.error('Error loading VRM:', error);
                    reject(error);
                }
            );
        });
    }

    async loadVRMFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = async (e) => {
                const arrayBuffer = e.target.result;
                const blob = new Blob([arrayBuffer]);
                const url = URL.createObjectURL(blob);

                try {
                    const vrm = await this.loadVRM(url);
                    URL.revokeObjectURL(url);
                    resolve(vrm);
                } catch (error) {
                    URL.revokeObjectURL(url);
                    reject(error);
                }
            };

            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsArrayBuffer(file);
        });
    }

    getVRM() {
        return this.vrm;
    }

    setBackgroundColor(color) {
        this.scene.background = new THREE.Color(color);
    }

    resetCamera() {
        this.camera.position.set(0, 1.4, 2);
        this.controls.target.set(0, 1.2, 0);
        this.controls.update();
    }

    onWindowResize() {
        if (!this.canvas) return;
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;

        if (width === 0 || height === 0) return;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        const deltaTime = this.clock.getDelta();

        if (this.vrm) {
            this.vrm.update(deltaTime);
        }

        if (this.animationManager) {
            this.animationManager.update(deltaTime);
        }

        this.controls.update();

        this.renderer.render(this.scene, this.camera);

        this.captureFrame();
    }

    startFrameCapture(wsConnection) {
        this.wsConnection = wsConnection;
        this.frameCapture.enabled = true;
        this.frameCapture.lastCaptureTime = Date.now();
        console.log('[Mirror] Frame capture started (10 FPS)');
    }

    stopFrameCapture() {
        this.frameCapture.enabled = false;
        console.log('[Mirror] Frame capture stopped');
    }

    captureFrame() {
        if (!this.frameCapture.enabled || !this.wsConnection) {
            return;
        }

        const now = Date.now();
        const timeSinceLastCapture = now - this.frameCapture.lastCaptureTime;

        if (timeSinceLastCapture < this.frameCapture.interval) {
            return;
        }

        try {
            const frameData = this.canvas.toDataURL('image/png');

            if (frameData.length > 2_000_000) {
                console.warn('[Mirror] Frame too large, skipping:', frameData.length);
                return;
            }

            const msg = {
                type: 'mirror_frame',
                frame_data: frameData,
                timestamp: now
            };

            if (this.wsConnection.readyState === WebSocket.OPEN) {
                this.wsConnection.send(JSON.stringify(msg));
                this.frameCapture.frameCount++;
            }

            this.frameCapture.lastCaptureTime = now;
        } catch (error) {
            console.error('[Mirror] Failed to capture frame:', error);
        }
    }

    getFrameStats() {
        return {
            frameCount: this.frameCapture.frameCount,
            fps: this.frameCapture.frameCount > 0 ? 10 : 0,
            lastFrameTime: this.frameCapture.lastCaptureTime
        };
    }

    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        if (this.vrm) {
            this.scene.remove(this.vrm.scene);
            VRMUtils.deepDispose(this.vrm.scene);
            this.vrm = null;
        }

        if (this.expressionController) {
            this.expressionController.dispose();
        }

        if (this.animationManager) {
            this.animationManager.dispose();
            this.animationManager = null;
        }

        // Deep clean scene
        if (this.scene) {
            this.scene.traverse((object) => {
                if (object.geometry) object.geometry.dispose();
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(material => material.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
        }

        if (this.renderer) {
            this.renderer.dispose();
            this.renderer.forceContextLoss();
            this.renderer.domElement = null;
            this.renderer = null;
        }

        if (this.controls) {
            this.controls.dispose();
        }
    }
}
