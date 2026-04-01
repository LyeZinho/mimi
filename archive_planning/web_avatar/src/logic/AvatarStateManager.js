/**
 * AvatarStateManager - Manages and broadcasts avatar state
 */
export class AvatarStateManager {
    constructor(websocketClient, posePlayer = null) {
        this.ws = websocketClient;
        this.posePlayer = posePlayer;
        this.state = {
            model: null,
            expression: 'neutral',
            animation: null,
            animationLoop: true,
            speaking: false,
            camera: {
                position: { x: 0, y: 1.4, z: 2 },
                target: { x: 0, y: 1.2, z: 0 }
            },
            background: '#1a1a2e'
        };

        this.listeners = new Set();
        this.isController = true; // Main page is controller, OBS is viewer
        
        if (this.ws) {
            this.setupPosePlaybackListener();
        }
    }

    /**
     * Setup listener for POSE_PLAYBACK events from orchestrator
     */
    setupPosePlaybackListener() {
        if (!this.ws || !this.ws.onMessage) {
            return;
        }
        
        this.ws.onMessage((message) => {
            if (message.type === 'POSE_PLAYBACK' && this.posePlayer) {
                this.handlePosePlayback(message);
            }
        });
    }

    /**
     * Handle pose playback event from WebSocket
     */
    async handlePosePlayback(message) {
        if (!this.posePlayer) return;
        
        const { frameId, fadeDuration = 0.5, poseData } = message;
        
        try {
            await this.posePlayer.playFrame(frameId, fadeDuration);
            console.log(`Played pose frame: ${frameId}`);
        } catch (error) {
            console.error('Error playing pose frame:', error);
        }
    }

    /**
     * Public method to play pose via frame ID and fade duration
     */
    async playPose(frameId, fadeDuration = 0.5) {
        if (!this.posePlayer) {
            console.warn('PosePlayer not initialized');
            return false;
        }
        
        const result = await this.posePlayer.playFrame(frameId, fadeDuration);
        return result.success;
    }

    /**
     * Set whether this instance controls or views state
     */
    setMode(isController) {
        this.isController = isController;
    }

    /**
     * Update state and broadcast if controller
     */
    setState(updates) {
        this.state = { ...this.state, ...updates };

        // Notify local listeners
        this.notifyListeners(updates);

        // Broadcast to other clients if controller
        if (this.isController && this.ws && this.ws.isConnected()) {
            this.broadcast();
        }
    }

    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Broadcast current state to all clients
     * Uses debounce to prevent network congestion
     */
    broadcast() {
        if (!this.ws || !this.ws.isConnected()) {
            return;
        }

        // Debounce: Cancel previous pending broadcast
        if (this.broadcastTimeout) {
            clearTimeout(this.broadcastTimeout);
        }

        this.broadcastTimeout = setTimeout(() => {
            const message = {
                type: 'state',
                state: this.state
            };

            this.ws.send(message);
            this.broadcastTimeout = null;
        }, 33); // Cap at ~30fps
    }

    /**
     * Apply state received from WebSocket
     */
    applyRemoteState(state) {
        if (this.isController) {
            // Controllers ignore remote state to avoid loops
            return;
        }

        console.log('Applying remote state:', state);
        this.state = { ...this.state, ...state };
        this.notifyListeners(state);
    }

    /**
     * Add state change listener
     */
    addListener(callback) {
        this.listeners.add(callback);
    }

    /**
     * Remove state change listener
     */
    removeListener(callback) {
        this.listeners.delete(callback);
    }

    /**
     * Notify all listeners of state changes
     */
    notifyListeners(changes) {
        this.listeners.forEach(listener => {
            try {
                listener(changes, this.state);
            } catch (error) {
                console.error('Error in state listener:', error);
            }
        });
    }

    /**
     * Convenience methods for common state updates
     */
    setModel(modelName) {
        this.setState({ model: modelName });
    }

    setExpression(expression) {
        this.setState({ expression });
    }

    setAnimation(animation, loop = true) {
        this.setState({ animation, animationLoop: loop });
    }

    setSpeaking(speaking) {
        this.setState({ speaking });
    }

    setCamera(position, target) {
        const camera = { ...this.state.camera };
        if (position) camera.position = position;
        if (target) camera.target = target;
        this.setState({ camera });
    }

    setBackground(color) {
        this.setState({ background: color });
    }

    /**
     * Throttle function to limit broadcast frequency
     */
    throttle(func, limit) {
        let inThrottle;
        return function () {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
}
