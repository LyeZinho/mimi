/**
 * ExpressionController - Manages VRM expressions and animations
 */
import { VRMExpressionPresetName } from '@pixiv/three-vrm';

export class ExpressionController {
    constructor(vrm) {
        this.vrm = vrm;
        this.currentExpression = 'neutral';
        this.isBlinking = false;
        this.isSpeaking = false;
        this.autoBlinkEnabled = true;
        this.autoBlinkInterval = null;

        // Expression mappings for VRM 1.0 and 0.0
        this.expressionMap = {
            neutral: VRMExpressionPresetName.Neutral,
            happy: VRMExpressionPresetName.Happy,
            sad: VRMExpressionPresetName.Sad,
            angry: VRMExpressionPresetName.Angry,
            surprised: VRMExpressionPresetName.Surprised,
            relaxed: VRMExpressionPresetName.Relaxed
        };

        this.startAutoBlink();
    }

    /**
     * Set expression with smooth transition
     */
    setExpression(expressionName, weight = 1.0, duration = 0.3) {
        if (!this.vrm || !this.vrm.expressionManager) {
            console.warn('VRM or expression manager not available');
            return;
        }

        const targetExpression = this.expressionMap[expressionName];

        if (!targetExpression) {
            console.warn(`Unknown expression: ${expressionName}`);
            return;
        }

        // Reset all expressions first
        this.resetExpressions();

        // Set new expression
        try {
            this.vrm.expressionManager.setValue(targetExpression, weight);
            this.currentExpression = expressionName;
            console.log(`Expression set to: ${expressionName}`);
        } catch (error) {
            console.error('Error setting expression:', error);
        }
    }

    /**
     * Reset all expressions to neutral
     */
    resetExpressions() {
        if (!this.vrm || !this.vrm.expressionManager) return;

        Object.values(this.expressionMap).forEach(expression => {
            try {
                this.vrm.expressionManager.setValue(expression, 0);
            } catch (error) {
                // Ignore errors for unsupported expressions
            }
        });
    }

    /**
     * Blink animation
     */
    async blink(duration = 150) {
        if (!this.vrm || !this.vrm.expressionManager || this.isBlinking) return;

        this.isBlinking = true;

        try {
            // Close eyes
            this.vrm.expressionManager.setValue(VRMExpressionPresetName.Blink, 1.0);

            await this.sleep(duration);

            // Open eyes
            this.vrm.expressionManager.setValue(VRMExpressionPresetName.Blink, 0);
        } catch (error) {
            console.error('Error during blink:', error);
        }

        this.isBlinking = false;
    }

    /**
     * Start automatic blinking
     */
    startAutoBlink() {
        if (this.autoBlinkInterval) {
            clearInterval(this.autoBlinkInterval);
        }

        this.autoBlinkInterval = setInterval(() => {
            if (this.autoBlinkEnabled && !this.isSpeaking) {
                this.blink();
            }
        }, 3000 + Math.random() * 2000); // Random interval between 3-5 seconds
    }

    /**
     * Stop automatic blinking
     */
    stopAutoBlink() {
        if (this.autoBlinkInterval) {
            clearInterval(this.autoBlinkInterval);
            this.autoBlinkInterval = null;
        }
    }

    /**
     * Toggle auto-blink
     */
    setAutoBlink(enabled) {
        this.autoBlinkEnabled = enabled;
        if (enabled) {
            this.startAutoBlink();
        } else {
            this.stopAutoBlink();
        }
    }

    /**
     * Simulate lip-sync (simple mouth movement)
     */
    async speak(duration = 2000) {
        if (!this.vrm || !this.vrm.expressionManager || this.isSpeaking) return;

        this.isSpeaking = true;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;

            if (elapsed >= duration) {
                // Stop speaking
                try {
                    this.vrm.expressionManager.setValue(VRMExpressionPresetName.Aa, 0);
                } catch (error) {
                    // Ignore if expression not supported
                }
                this.isSpeaking = false;
                return;
            }

            // Animate mouth with sine wave
            const mouthValue = Math.abs(Math.sin(elapsed * 0.01)) * 0.7;

            try {
                this.vrm.expressionManager.setValue(VRMExpressionPresetName.Aa, mouthValue);
            } catch (error) {
                // Ignore if expression not supported
            }

            requestAnimationFrame(animate);
        };

        animate();
    }

    /**
     * Apply custom blendshape values
     */
    setBlendShape(name, value) {
        if (!this.vrm || !this.vrm.expressionManager) return;

        try {
            this.vrm.expressionManager.setValue(name, value);
        } catch (error) {
            console.warn(`Blendshape ${name} not found or not supported`);
        }
    }

    /**
     * Get available expressions
     */
    getAvailableExpressions() {
        if (!this.vrm || !this.vrm.expressionManager) return [];

        const expressions = [];
        const manager = this.vrm.expressionManager;

        // Try to get all available expressions
        Object.entries(this.expressionMap).forEach(([key, value]) => {
            try {
                // Check if expression exists by trying to get it
                if (manager.getExpression(value)) {
                    expressions.push(key);
                }
            } catch (error) {
                // Expression not available
            }
        });

        return expressions;
    }

    /**
     * Get model information
     */
    getModelInfo() {
        if (!this.vrm) return null;

        const info = {
            version: this.vrm.meta?.metaVersion || 'Unknown',
            name: this.vrm.meta?.name || 'Unknown',
            author: this.vrm.meta?.authors?.[0] || this.vrm.meta?.author || 'Unknown',
            expressions: this.getAvailableExpressions()
        };

        return info;
    }

    /**
     * Utility: Sleep function
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Cleanup
     */
    dispose() {
        this.stopAutoBlink();
        this.resetExpressions();
    }
}
