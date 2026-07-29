/**
 * WebSocket Connection & Real-Time Telemetry Stream Manager.
 */

class TelemetryWebSocket {
    constructor(onMessageCallback, onStatusChangeCallback) {
        this.ws = null;
        this.onMessage = onMessageCallback;
        this.onStatusChange = onStatusChangeCallback;
        this.reconnectInterval = 2000;
        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log(`[WebSocket] Connecting to ${wsUrl}...`);
        if (this.onStatusChange) this.onStatusChange('CONNECTING');

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('[WebSocket] Connection Established.');
                if (this.onStatusChange) this.onStatusChange('CONNECTED');
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (this.onMessage) this.onMessage(data);
                } catch (e) {
                    console.error('[WebSocket] JSON Parse Error:', e);
                }
            };

            this.ws.onclose = () => {
                console.warn('[WebSocket] Connection Closed. Reconnecting in 2s...');
                if (this.onStatusChange) this.onStatusChange('DISCONNECTED');
                setTimeout(() => this.connect(), this.reconnectInterval);
            };

            this.ws.onerror = (err) => {
                console.error('[WebSocket] Error:', err);
                if (this.ws) this.ws.close();
            };
        } catch (e) {
            console.error('[WebSocket] Failed to initialize:', e);
            setTimeout(() => this.connect(), this.reconnectInterval);
        }
    }
}
