/**
 * AnimationManager - Handles FBX animation loading and mixing for VRM
 */
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

const mixamoVRMRigMap = {
    mixamorigHips: 'hips',
    mixamorigSpine: 'spine',
    mixamorigSpine1: 'chest',
    mixamorigSpine2: 'upperChest',
    mixamorigNeck: 'neck',
    mixamorigHead: 'head',
    mixamorigLeftShoulder: 'leftShoulder',
    mixamorigLeftArm: 'leftUpperArm',
    mixamorigLeftForeArm: 'leftLowerArm',
    mixamorigLeftHand: 'leftHand',
    mixamorigLeftHandThumb1: 'leftThumbMetacarpal',
    mixamorigLeftHandThumb2: 'leftThumbProximal',
    mixamorigLeftHandThumb3: 'leftThumbDistal',
    mixamorigLeftHandIndex1: 'leftIndexProximal',
    mixamorigLeftHandIndex2: 'leftIndexIntermediate',
    mixamorigLeftHandIndex3: 'leftIndexDistal',
    mixamorigLeftHandMiddle1: 'leftMiddleProximal',
    mixamorigLeftHandMiddle2: 'leftMiddleIntermediate',
    mixamorigLeftHandMiddle3: 'leftMiddleDistal',
    mixamorigLeftHandRing1: 'leftRingProximal',
    mixamorigLeftHandRing2: 'leftRingIntermediate',
    mixamorigLeftHandRing3: 'leftRingDistal',
    mixamorigLeftHandPinky1: 'leftLittleProximal',
    mixamorigLeftHandPinky2: 'leftLittleIntermediate',
    mixamorigLeftHandPinky3: 'leftLittleDistal',
    mixamorigRightShoulder: 'rightShoulder',
    mixamorigRightArm: 'rightUpperArm',
    mixamorigRightForeArm: 'rightLowerArm',
    mixamorigRightHand: 'rightHand',
    mixamorigRightHandPinky1: 'rightLittleProximal',
    mixamorigRightHandPinky2: 'rightLittleIntermediate',
    mixamorigRightHandPinky3: 'rightLittleDistal',
    mixamorigRightHandRing1: 'rightRingProximal',
    mixamorigRightHandRing2: 'rightRingIntermediate',
    mixamorigRightHandRing3: 'rightRingDistal',
    mixamorigRightHandMiddle1: 'rightMiddleProximal',
    mixamorigRightHandMiddle2: 'rightMiddleIntermediate',
    mixamorigRightHandMiddle3: 'rightMiddleDistal',
    mixamorigRightHandIndex1: 'rightIndexProximal',
    mixamorigRightHandIndex2: 'rightIndexIntermediate',
    mixamorigRightHandIndex3: 'rightIndexDistal',
    mixamorigRightHandThumb1: 'rightThumbMetacarpal',
    mixamorigRightHandThumb2: 'rightThumbProximal',
    mixamorigRightHandThumb3: 'rightThumbDistal',
    mixamorigLeftUpLeg: 'leftUpperLeg',
    mixamorigLeftLeg: 'leftLowerLeg',
    mixamorigLeftFoot: 'leftFoot',
    mixamorigLeftToeBase: 'leftToes',
    mixamorigRightUpLeg: 'rightUpperLeg',
    mixamorigRightLeg: 'rightLowerLeg',
    mixamorigRightFoot: 'rightFoot',
    mixamorigRightToeBase: 'rightToes',
};

export class AnimationManager {
    constructor(vrm) {
        this.vrm = vrm;
        this.mixer = new THREE.AnimationMixer(vrm.scene);
        this.animations = new Map(); // Store loaded animations
        this.currentAction = null;
        this.loader = new FBXLoader();
    }

    /**
     * Load an FBX animation from URL
     */
    async loadAnimation(name, url) {
        if (this.animations.has(name)) {
            return this.animations.get(name);
        }

        const loader = new FBXLoader();
        return loader.loadAsync(url).then((asset) => {
            const clip = THREE.AnimationClip.findByName(asset.animations, 'mixamo.com'); // extract the AnimationClip

            // If 'mixamo.com' not found, take the first one or try to find by other means
            const targetClip = clip || asset.animations[0];
            if (!targetClip) {
                throw new Error("No animation clip found");
            }

            const tracks = []; // KeyframeTracks compatible with VRM will be added here

            const restRotationInverse = new THREE.Quaternion();
            const parentRestWorldRotation = new THREE.Quaternion();
            const _quatA = new THREE.Quaternion();
            const _vec3 = new THREE.Vector3();

            // Adjust with reference to hips height.
            const motionHips = asset.getObjectByName('mixamorigHips');
            if (!motionHips) {
                console.warn("mixamorigHips not found in FBX, skipping retargeting");
                this.animations.set(name, targetClip);
                return targetClip;
            }

            const motionHipsHeight = motionHips.position.y;
            const vrmHipsHeight = this.vrm.humanoid.normalizedRestPose.hips.position[1];
            const hipsPositionScale = vrmHipsHeight / motionHipsHeight;

            targetClip.tracks.forEach((track) => {
                // Convert each tracks for VRM use, and push to `tracks`
                const trackSplitted = track.name.split('.');
                const mixamoRigName = trackSplitted[0];
                const vrmBoneName = mixamoVRMRigMap[mixamoRigName];
                const vrmNodeName = this.vrm.humanoid?.getNormalizedBoneNode(vrmBoneName)?.name;
                const mixamoRigNode = asset.getObjectByName(mixamoRigName);

                if (vrmNodeName != null) {
                    const propertyName = trackSplitted[1];

                    // Store rotations of rest-pose.
                    mixamoRigNode.getWorldQuaternion(restRotationInverse).invert();
                    mixamoRigNode.parent.getWorldQuaternion(parentRestWorldRotation);

                    if (track instanceof THREE.QuaternionKeyframeTrack) {
                        // Retarget rotation of mixamoRig to NormalizedBone.
                        for (let i = 0; i < track.values.length; i += 4) {
                            const flatQuaternion = track.values.slice(i, i + 4);
                            _quatA.fromArray(flatQuaternion);

                            // Parent rest world rotation * track rotation * rest rotation inverse
                            _quatA
                                .premultiply(parentRestWorldRotation)
                                .multiply(restRotationInverse);

                            _quatA.toArray(flatQuaternion);

                            flatQuaternion.forEach((v, index) => {
                                track.values[index + i] = v;
                            });
                        }

                        tracks.push(
                            new THREE.QuaternionKeyframeTrack(
                                `${vrmNodeName}.${propertyName}`,
                                track.times,
                                track.values.map((v, i) => (this.vrm.meta?.metaVersion === '0' && i % 2 === 0 ? -v : v)),
                            ),
                        );
                    } else if (track instanceof THREE.VectorKeyframeTrack) {
                        const value = track.values.map((v, i) => (this.vrm.meta?.metaVersion === '0' && i % 3 !== 1 ? -v : v) * hipsPositionScale);
                        tracks.push(new THREE.VectorKeyframeTrack(`${vrmNodeName}.${propertyName}`, track.times, value));
                    }
                }
            });

            const newClip = new THREE.AnimationClip(name, targetClip.duration, tracks);
            this.animations.set(name, newClip);
            console.log(`Animation loaded and retargeted: ${name}`);
            return newClip;
        });
    }

    // Deprecated old method
    retargetMixamoClip(clip, vrm) { return clip; }

    /**
     * Play a loaded animation
     */
    play(name, fadeDuration = 0.5) {
        const clip = this.animations.get(name);
        if (!clip) {
            console.warn(`Animation not found: ${name}`);
            return;
        }

        const action = this.mixer.clipAction(clip);

        if (this.currentAction && this.currentAction !== action) {
            this.currentAction.fadeOut(fadeDuration);
        }

        action
            .reset()
            .setEffectiveTimeScale(1)
            .setEffectiveWeight(1)
            .fadeIn(fadeDuration)
            .play();

        this.currentAction = action;
    }

    stop(fadeDuration = 0.5) {
        if (this.currentAction) {
            this.currentAction.fadeOut(fadeDuration);
        }
    }

    update(deltaTime) {
        this.mixer.update(deltaTime);
    }

    /**
     * Set a static pose (mock implementation)
     */
    setPose(poseName) {
        // Reset/Stop current animation
        this.stop();

        if (!this.vrm || !this.vrm.humanoid) return;

        const humanoid = this.vrm.humanoid;
        const resetRotation = (boneName) => {
            const node = humanoid.getNormalizedBoneNode(boneName);
            if (node) node.rotation.set(0, 0, 0);
        };

        // Simple reset of arms
        ['leftUpperArm', 'rightUpperArm', 'leftLowerArm', 'rightLowerArm'].forEach(resetRotation);

        if (poseName === 'Wave') {
            const ra = humanoid.getNormalizedBoneNode('rightUpperArm');
            const rf = humanoid.getNormalizedBoneNode('rightLowerArm');
            if (ra) ra.rotation.z = -Math.PI * 0.4;
            if (ra) ra.rotation.x = 0.5;
            if (rf) rf.rotation.z = -0.5;
        } else if (poseName === 'Think') {
            const ra = humanoid.getNormalizedBoneNode('rightUpperArm');
            const rf = humanoid.getNormalizedBoneNode('rightLowerArm');
            if (ra) ra.rotation.z = -Math.PI * 0.3;
            if (ra) ra.rotation.x = 0.8;
            if (rf) rf.rotation.x = 1.5; // Hand to chin approx
        }

        // Note: Real poses should use animation clips or full skeleton setting
        console.log(`Pose set: ${poseName}`);
    }
    dispose() {
        this.stop(0);
        if (this.mixer) {
            this.mixer.stopAllAction();
            this.mixer.uncacheRoot(this.mixer.getRoot());
            this.mixer = null;
        }
        this.currentAction = null;
        this.animations.clear();
        this.vrm = null;
        this.loader = null;
    }
}
