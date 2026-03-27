/**
 * PosePlayer - Test suite
 * TDD: Failing tests first, then implementation
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as THREE from 'three';
import { PosePlayer } from '../logic/PosePlayer.js';
import { AvatarStateManager } from '../logic/AvatarStateManager.js';

describe('PosePlayer - Task 6A: Basic Structure', () => {
    let mockVRM;
    let mockScene;
    let posePlayer;

    beforeEach(() => {
        // Mock VRM model
        mockVRM = {
            scene: new THREE.Scene(),
            humanoid: {
                getNormalizedBoneNode: vi.fn((boneName) => {
                    const bone = new THREE.Object3D();
                    bone.name = boneName;
                    bone.rotation = new THREE.Euler();
                    bone.quaternion = new THREE.Quaternion();
                    return bone;
                }),
                normalizedRestPose: {
                    hips: { position: [0, 1, 0] }
                }
            }
        };

        mockScene = new THREE.Scene();
        posePlayer = new PosePlayer(mockVRM, mockScene);
    });

    // Task 6A Tests: Skeleton structure
    it('should construct with VRM and scene', () => {
        expect(posePlayer).toBeDefined();
        expect(posePlayer.vrm).toBe(mockVRM);
        expect(posePlayer.scene).toBe(mockScene);
    });

    it('should have loadPoses async method returning Promise<boolean>', async () => {
        expect(typeof posePlayer.loadPoses).toBe('function');
        const result = posePlayer.loadPoses('path/to/poses', 'pose1');
        expect(result).toBeInstanceOf(Promise);
    });

    it('loadPoses should return false for missing paths', async () => {
        const result = await posePlayer.loadPoses(null, 'pose1');
        expect(result).toBe(false);
    });

    it('should have playFrame async method', () => {
        expect(typeof posePlayer.playFrame).toBe('function');
        const result = posePlayer.playFrame('frame1', 0.5);
        expect(result).toBeInstanceOf(Promise);
    });

    it('playFrame should return object with success, frameId, timestamp', async () => {
        const result = await posePlayer.playFrame('frame1', 0.5);
        expect(result).toHaveProperty('success');
        expect(result).toHaveProperty('frameId');
        expect(result).toHaveProperty('timestamp');
    });

    it('should have stopPlayback method', () => {
        expect(typeof posePlayer.stopPlayback).toBe('function');
        expect(() => posePlayer.stopPlayback()).not.toThrow();
    });

    it('should have getCurrentFrameId method', () => {
        expect(typeof posePlayer.getCurrentFrameId).toBe('function');
        const frameId = posePlayer.getCurrentFrameId();
        expect(frameId === null || typeof frameId === 'string').toBe(true);
    });

    it('getCurrentFrameId should return null initially', () => {
        const frameId = posePlayer.getCurrentFrameId();
        expect(frameId).toBeNull();
    });
});

describe('PosePlayer - Task 6B: Bone Mapping', () => {
    let mockVRM;
    let posePlayer;

    beforeEach(() => {
        // Mock VRM with bone structure
        const createBone = (name) => {
            const bone = new THREE.Object3D();
            bone.name = name;
            bone.quaternion = new THREE.Quaternion();
            return bone;
        };

        mockVRM = {
            scene: new THREE.Scene(),
            humanoid: {
                getNormalizedBoneNode: vi.fn((boneName) => {
                    const boneMap = {
                        'hips': createBone('Armature.Hips'),
                        'leftShoulder': createBone('Armature.ShoulderL'),
                        'rightShoulder': createBone('Armature.ShoulderR'),
                        'leftFoot': createBone('Armature.FootL'),
                        'rightFoot': createBone('Armature.FootR'),
                    };
                    return boneMap[boneName] || null;
                })
            }
        };

        posePlayer = new PosePlayer(mockVRM, new THREE.Scene());
    });

    it('should have static createBoneMapping method', () => {
        expect(typeof PosePlayer.createBoneMapping).toBe('function');
    });

    it('createBoneMapping should return Map with MediaPipe indices', () => {
        const mapping = PosePlayer.createBoneMapping(mockVRM);
        expect(mapping).toBeInstanceOf(Map);
    });

    it('createBoneMapping should map MediaPipe 11 (L shoulder) to VRM bone', () => {
        const mapping = PosePlayer.createBoneMapping(mockVRM);
        expect(mapping.has(11)).toBe(true);
        expect(typeof mapping.get(11)).toBe('string');
    });

    it('createBoneMapping should map MediaPipe 12 (R shoulder) to VRM bone', () => {
        const mapping = PosePlayer.createBoneMapping(mockVRM);
        expect(mapping.has(12)).toBe(true);
    });

    it('createBoneMapping should map MediaPipe 25 (L foot) to VRM bone', () => {
        const mapping = PosePlayer.createBoneMapping(mockVRM);
        expect(mapping.has(25)).toBe(true);
    });

    it('createBoneMapping should map MediaPipe 26 (R foot) to VRM bone', () => {
        const mapping = PosePlayer.createBoneMapping(mockVRM);
        expect(mapping.has(26)).toBe(true);
    });
});

describe('PosePlayer - Task 6C: Frame Playback Logic', () => {
    let mockVRM;
    let posePlayer;
    let mockWS;

    beforeEach(() => {
        const createBone = (name) => {
            const bone = new THREE.Object3D();
            bone.name = name;
            bone.quaternion = new THREE.Quaternion();
            bone.rotation = new THREE.Euler();
            return bone;
        };

        mockVRM = {
            scene: new THREE.Scene(),
            humanoid: {
                getNormalizedBoneNode: vi.fn((boneName) => {
                    return createBone(boneName);
                })
            }
        };

        mockWS = {
            send: vi.fn(),
            on: vi.fn(),
            off: vi.fn()
        };

        posePlayer = new PosePlayer(mockVRM, new THREE.Scene());
    });

    it('should apply quaternion rotations to bones', async () => {
        const mockFrame = {
            body_pose: Array(33).fill([0, 0, 0])
        };

        const result = await posePlayer.playFrame('frame1', 0.1);
        expect(result).toHaveProperty('success');
        expect(result.success).toBe(true);
    });

    it('playFrame should track current frame ID', async () => {
        await posePlayer.playFrame('frame42', 0.5);
        expect(posePlayer.getCurrentFrameId()).toBe('frame42');
    });

    it('playFrame should accept fadeDuration parameter', async () => {
        const result = await posePlayer.playFrame('frame1', 1.0);
        expect(result.success).toBe(true);
    });

    it('stopPlayback should reset frame ID', async () => {
        await posePlayer.playFrame('frame1', 0.5);
        expect(posePlayer.getCurrentFrameId()).toBe('frame1');
        posePlayer.stopPlayback();
        expect(posePlayer.getCurrentFrameId()).toBeNull();
    });
});

describe('PosePlayer - Task 6D: WebSocket Integration', () => {
    let mockVRM;
    let mockWS;
    let posePlayer;
    let stateManager;

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
            send: vi.fn(),
            on: vi.fn(),
            off: vi.fn(),
            onMessage: vi.fn(),
            isConnected: vi.fn(() => true),
            onMessageCallback: null
        };

        posePlayer = new PosePlayer(mockVRM, new THREE.Scene());
    });

    it('should have registerWebSocketListener method', () => {
        expect(typeof posePlayer.registerWebSocketListener).toBe('function');
    });

    it('should handle POSE_PLAYBACK event', async () => {
        let eventHandler;
        mockWS.on = vi.fn((event, handler) => {
            if (event === 'POSE_PLAYBACK') {
                eventHandler = handler;
            }
        });

        posePlayer.registerWebSocketListener(mockWS);

        // Verify event listener was registered
        expect(mockWS.on).toHaveBeenCalledWith(
            'POSE_PLAYBACK',
            expect.any(Function)
        );
    });

    it('AvatarStateManager should accept posePlayer in constructor', () => {
        const stateManager = new AvatarStateManager(mockWS, posePlayer);
        expect(stateManager.posePlayer).toBe(posePlayer);
    });

    it('AvatarStateManager should expose playPose method', () => {
        const stateManager = new AvatarStateManager(mockWS, posePlayer);
        expect(typeof stateManager.playPose).toBe('function');
    });

    it('playPose should call posePlayer.playFrame', async () => {
        const spyPlayFrame = vi.spyOn(posePlayer, 'playFrame');
        
        const stateManager = new AvatarStateManager(mockWS, posePlayer);
        await stateManager.playPose('frame123', 0.5);
        
        expect(spyPlayFrame).toHaveBeenCalledWith('frame123', 0.5);
    });
});
