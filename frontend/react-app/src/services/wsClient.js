export function createWS(sessionId, onMessage) {
  const url = `ws://127.0.0.1:8000/ws/stream?session=${sessionId}`

  let ws = new WebSocket(url)

  ws.onopen = () => {
    console.log("WS connected")
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage && onMessage(data)
    } catch (e) {
      console.warn("WS parse error", e)
    }
  }

  ws.onerror = (e) => {
    console.warn("WS error", e)
  }

  ws.onclose = () => {
    console.log("WS closed")
  }

  return {
    send: (data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    },
    close: () => ws.close()
  }
}