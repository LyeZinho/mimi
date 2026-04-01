import { describe, it, expect, beforeEach } from 'vitest';
import { AvatarStateManager } from '../logic/AvatarStateManager.js';

describe('Backward Compatibility', () => {
    let stateManager;
    let mockWS;

    beforeEach(() => {
        mockWS = {
            isConnected: () => true,
            send: () => {}
        };
        stateManager = new AvatarStateManager(mockWS);
    });

    it('AvatarStateManager works without posePlayer (backward compatible)', () => {
        expect(stateManager.posePlayer).toBeNull();
    });

    it('setState still works without posePlayer', () => {
        stateManager.setState({ expression: 'happy' });
        expect(stateManager.getState().expression).toBe('happy');
    });

    it('setExpression still works', () => {
        stateManager.setExpression('sad');
        expect(stateManager.getState().expression).toBe('sad');
    });

    it('setAnimation still works', () => {
        stateManager.setAnimation('wave', true);
        expect(stateManager.getState().animation).toBe('wave');
        expect(stateManager.getState().animationLoop).toBe(true);
    });

    it('broadcast still works', () => {
        expect(() => stateManager.broadcast()).not.toThrow();
    });
});
