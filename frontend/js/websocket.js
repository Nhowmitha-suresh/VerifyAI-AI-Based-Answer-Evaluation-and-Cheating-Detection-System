/**
 * WebSocket Connection & Real-Time Telemetry Stream Manager.
 */

class TelemetryWebSocket {
    constructor(onMessageCallback, onStatusChangeCallback) {
        self.ws = null;
        self.onMessage = onMessageCallback;
        self.onStatusChange = onStatusChangeCallback;
        self.reconnectInterval = 2000;
        self.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log(`[WebSocket] Connecting to ${wsUrl}...`);
        if (self.onStatusChange) self.onStatusChange('CONNECTING');

        try {
            self.ws = new WebSocket(wsUrl);

            self.ws.onopen = () => {
                console.log('[WebSocket] Connection Established.');
                if (self.onStatusChange) self.onStatusChange('CONNECTED');
            };

            self.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (self.onMessage) self.onMessage(data);
                } catch (e) {
                    console.error('[WebSocket] JSON Parse Error:', e);
                }
            };

            self.ws.onclose = () => {
                console.warn('[WebSocket] Connection Closed. Reconnecting in 2s...');
                if (self.onStatusChange) self.onStatusChange('DISCONNECTED');
                setTimeout(() => self.connect(), self.reconnectInterval);
            };

            self.ws.onerror = (err) => {
                console.error('[WebSocket] Error:', err);
                self.ws.close();
            };
        } catch (e) {
            console.error('[WebSocket] Failed to initialize:', e);
            setTimeout(() => self.connect(), self.reconnectInterval);
        }
    }
}
