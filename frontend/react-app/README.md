verifAI React demo

Quick start:

1. Install dependencies

```bash
cd frontend/react-app
npm install
```

2. Run dev server

```bash
npm run dev
```

Open the site (Vite will show the URL). Start camera and then Start Stream to begin sending frames to backend `ws://127.0.0.1:8000/ws/stream`.

Notes:
- Ensure the backend FastAPI server is running (uvicorn app.main:app --reload).
- This demo sends low-frequency JPEG frames (~5 fps) for CPU-friendly local testing.
- For production use, switch to secure WebSocket (wss) behind HTTPS and implement auth, rate-limiting, and frame batching/compression.
