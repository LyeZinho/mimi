/**
 * WebSocketClient - Handles WebSocket communication with Python backend
 */
export class WebSocketClient {
    constructor(url = 'ws://localhost:8765') {
        this.url = url;
        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this._messageHandlers = new Set();
        this._statusHandlers = new Set();
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        return new Promise((resolve, reject) => {
            try {
                this.updateStatus('connecting');
                this.ws = new WebSocket(this.url);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    
                    this.sendIdentify().then(() => {
                        this.updateStatus('connected');
                        resolve();
                    }).catch(err => {
                        console.error('Failed to send identify:', err);
                        reject(err);
                    });
                };

                this.ws.onmessage = (event) => {
                    this.handleMessage(event.data);
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.updateStatus('error');
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.connected = false;
                    this.updateStatus('disconnected');
                    this.attemptReconnect();
                };

            } catch (error) {
                console.error('Failed to connect:', error);
                this.updateStatus('error');
                reject(error);
            }
        });
    }

    /**
     * Send identify message to establish client role
     */
    sendIdentify() {
        return new Promise((resolve, reject) => {
            try {
                const clientId = `browser_${Math.random().toString(36).substr(2, 9)}`;
                const identifyMsg = JSON.stringify({
                    type: 'identify',
                    role: 'browser',
                    client_id: clientId
                });
                
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(identifyMsg);
                    console.log(`Identified as browser: ${clientId}`);
                    resolve();
                } else {
                    reject(new Error('WebSocket not ready'));
                }
            } catch (error) {
                console.error('Error sending identify:', error);
                reject(error);
            }
        });
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
            this.ws.close();
            this.ws = null;
            this.connected = false;
            this.updateStatus('disconnected');
        }
    }

    /**
     * Attempt to reconnect
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect().catch(error => {
                console.error('Reconnection failed:', error);
            });
        }, this.reconnectDelay);
    }

    /**
     * Handle incoming messages
     */
    handleMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('Received message:', message);

            for (const handler of this._messageHandlers) {
                try {
                    handler(message);
                } catch (err) {
                    console.error('Error in message handler:', err);
                }
            }
        } catch (error) {
            console.error('Error parsing message:', error);
        }
    }

    /**
     * Send message to server
     */
    send(data) {
        if (!this.connected || !this.ws) {
            console.warn('WebSocket not connected');
            return false;
        }

        try {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.ws.send(message);
            return true;
        } catch (error) {
            console.error('Error sending message:', error);
            return false;
        }
    }

    /**
     * Update connection status
     */
    updateStatus(status) {
        for (const handler of this._statusHandlers) {
            try {
                handler(status);
            } catch (err) {
                console.error('Error in status handler:', err);
            }
        }
    }

    /**
     * Subscribe to messages. Returns unsubscribe function.
     */
    onMessage(callback) {
        this._messageHandlers.add(callback);
        return () => this._messageHandlers.delete(callback);
    }

    /**
     * Subscribe to status changes. Returns unsubscribe function.
     */
    onStatusChange(callback) {
        this._statusHandlers.add(callback);
        return () => this._statusHandlers.delete(callback);
    }

    /**
     * Check if connected
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Set WebSocket URL
     */
    setUrl(url) {
        if (this.connected) {
            console.warn('Cannot change URL while connected');
            return false;
        }
        this.url = url;
        return true;
    }
}
