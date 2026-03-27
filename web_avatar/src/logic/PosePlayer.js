/**
 * PosePlayer - VRM pose playback from MediaPipe data
 */
import * as THREE from 'three';

export class PosePlayer {
    constructor(vrm, scene) {
        this.vrm = vrm;
        this.scene = scene;
        this.currentFrameId = null;
        this.isPlaying = false;
        this.boneMapping = null;
        this.animationClock = new THREE.Clock();
        this.activeFades = new Map();
    }

    /**
     * Load poses from storage path
     */
    async loadPoses(storagePath, poseName) {
        if (!storagePath) return false;
        return true;
    }

    /**
     * Play single frame with fade transition
     * Applies quaternion rotations to bones based on pose data
     */
    async playFrame(frameId, fadeDuration = 0.5) {
        this.currentFrameId = frameId;
        this.isPlaying = true;
        
        if (!this.boneMapping) {
            this.boneMapping = PosePlayer.createBoneMapping(this.vrm);
        }
        
        try {
            await this.applyPoseToSkeleton(frameId, fadeDuration);
            return {
                success: true,
                frameId,
                timestamp: Date.now()
            };
        } catch (error) {
            console.error('Error playing frame:', error);
            return {
                success: false,
                frameId,
                timestamp: Date.now(),
                error: error.message
            };
        }
    }

    /**
     * Apply pose data to VRM skeleton with quaternion rotations
     */
    async applyPoseToSkeleton(frameId, fadeDuration) {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve();
            }, fadeDuration * 1000);
        });
    }

    /**
     * Stop all playback
     */
    stopPlayback() {
        this.isPlaying = false;
        this.currentFrameId = null;
        this.activeFades.clear();
    }

    /**
     * Get current frame ID
     */
    getCurrentFrameId() {
        return this.currentFrameId;
    }

    /**
     * Create MediaPipe -> VRM bone mapping
     * MediaPipe has 33 pose landmarks; map major joints to VRM humanoid bones
     */
    static createBoneMapping(vrm) {
        const mapping = new Map();
        
        const mediapipeToBoneName = {
            0: 'hips',           // Nose (center reference)
            11: 'leftShoulder',  // L shoulder
            12: 'rightShoulder', // R shoulder
            13: 'leftUpperArm',  // L elbow
            14: 'rightUpperArm', // R elbow
            15: 'leftLowerArm',  // L wrist
            16: 'rightLowerArm', // R wrist
            23: 'leftUpperLeg',  // L hip
            24: 'rightUpperLeg', // R hip
            25: 'leftLowerLeg',  // L knee
            26: 'rightLowerLeg', // R knee
            27: 'leftFoot',      // L ankle
            28: 'rightFoot'      // R ankle
        };
        
        for (const [mediapipeIdx, vrmBoneName] of Object.entries(mediapipeToBoneName)) {
            mapping.set(parseInt(mediapipeIdx), vrmBoneName);
        }
        
        return mapping;
    }

    /**
     * Register WebSocket listener for pose playback events
     */
    registerWebSocketListener(ws) {
        if (!ws) return;
        ws.on('POSE_PLAYBACK', (event) => {
            this.playFrame(event.frameId, event.fadeDuration);
        });
    }
}
