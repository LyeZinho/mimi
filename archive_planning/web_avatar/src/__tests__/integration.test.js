import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as THREE from 'three';
import { PosePlayer } from '../logic/PosePlayer.js';
import { AvatarStateManager } from '../logic/AvatarStateManager.js';

describe('Integration: Orchestrator → PosePlayer → Avatar', () => {
    let posePlayer;
    let stateManager;
    let mockVRM;
    let mockWS;

    beforeEach(() => {
        const createBone = (name) => {
            const bone = new THREE.Object3D();
            bone.name = name;
            bone.quaternion = new THREE.Quaternion();
            return bone;
        };

        mockVRM = {
            scene: new THREE.Scene(),
            humanoid: {
                getNormalizedBoneNode: vi.fn((boneName) => createBone(boneName))
            }
        };

        mockWS = {
            isConnected: () => true,
            send: vi.fn(),
            onMessage: vi.fn(),
            onMessageCallback: null
        };

        posePlayer = new PosePlayer(mockVRM, new THREE.Scene());
        stateManager = new AvatarStateManager(mockWS, posePlayer);
    });

    it('should orchestrate pose playback event → state manager → player', async () => {
        const frameId = 'frame_test_123';
        const fadeDuration = 0.5;

        const result = await stateManager.playPose(frameId, fadeDuration);
        
        expect(result).toBe(true);
        expect(posePlayer.getCurrentFrameId()).toBe(frameId);
    });

    it('should handle multiple frames in sequence', async () => {
        const result1 = await stateManager.playPose('frame1', 0.1);
        expect(result1).toBe(true);
        expect(posePlayer.getCurrentFrameId()).toBe('frame1');

        const result2 = await stateManager.playPose('frame2', 0.1);
        expect(result2).toBe(true);
        expect(posePlayer.getCurrentFrameId()).toBe('frame2');
    });

    it('should maintain coexistence with expression control', async () => {
        stateManager.setExpression('happy');
        await stateManager.playPose('frame1', 0.1);

        const state = stateManager.getState();
        expect(state.expression).toBe('happy');
        expect(posePlayer.getCurrentFrameId()).toBe('frame1');
    });

    it('should handle stopPlayback', async () => {
        await stateManager.playPose('frame1', 0.1);
        expect(posePlayer.getCurrentFrameId()).toBe('frame1');

        posePlayer.stopPlayback();
        expect(posePlayer.getCurrentFrameId()).toBeNull();
    });
});
