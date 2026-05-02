import React, { useRef, useEffect, useState } from "react"
import InterviewFlow from "../services/interviewFlow"
import WarningSystem from "./WarningSystem"

export default function InterviewScreen({
  duration = 120,
  question = "Explain a time you solved a hard problem."
}) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const flowRef = useRef(null)
  const intervalRef = useRef(null)

  const [mediaStream, setMediaStream] = useState(null)
  const [secondsLeft, setSecondsLeft] = useState(duration)
  const [phase, setPhase] = useState("idle")
  const [alerts, setAlerts] = useState([])
  const [integrityScore, setIntegrityScore] = useState(null)
  const [cameraStatus, setCameraStatus] = useState('idle')
  const [wsStatus, setWsStatus] = useState('idle')

  // ⏱ Timer
  useEffect(() => {
    if (phase !== "listening") return
    if (secondsLeft <= 0) stopInterview()

    const id = setInterval(() => {
      setSecondsLeft(s => s - 1)
    }, 1000)

    return () => clearInterval(id)
  }, [phase, secondsLeft])

  // 🎥 Camera
  const initCamera = async () => {
    try {
      console.log('Step 1: Starting camera')
      setCameraStatus('starting')

      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })

      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }

      setMediaStream(stream)
      setCameraStatus('ok')
      console.log('Step 2: Camera success')
      return stream
    } catch (err) {
      console.error('Camera error:', err)
      if (err && err.name === 'NotAllowedError') {
        setCameraStatus('denied')
        alert('Camera/microphone access was denied. Please enable permissions and try again.')
      } else if (err && (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError')) {
        setCameraStatus('notfound')
        alert('No camera or microphone found on this device.')
      } else {
        setCameraStatus('error')
        alert('Camera error: ' + (err.message || err))
      }
      throw err
    }
  }

  // 📡 Frame Streaming
  const startStreaming = () => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext("2d")

    intervalRef.current = setInterval(() => {
      try {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)

        canvas.toBlob(async blob => {
          if (!blob) return
          const buf = await blob.arrayBuffer()
          flowRef.current?.sendFrame(buf)
        }, "image/jpeg", 0.6)

      } catch (e) {
        console.warn("Frame capture error", e)
      }
    }, 1000)
  }

  const stopStreaming = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  // ▶️ START
  const startInterview = async () => {
    if (phase !== "idle") return

    try {
      console.log('StartInterview: begin')
      setPhase("starting")

      console.log('Step 1: before camera start')
      await initCamera()
      console.log('Step 3: Camera initialized')

      console.log('Step 4: creating InterviewFlow')
      const flow = new InterviewFlow(ev => {
        if (ev.type === "phase") {
          setPhase(ev.phase)
        }

        if (ev.type === "ws" && ev.msg) {
          if (ev.msg.alerts) setAlerts(ev.msg.alerts)
          if (typeof ev.msg.integrity !== "undefined") {
            setIntegrityScore(ev.msg.integrity)
          }
        }
      })

      flowRef.current = flow

      try{
        console.log('Step 4a: connecting WS (via flow.start)')
        setWsStatus('connecting')
        await flow.start()
        // register ws client events if available
        if(flowRef.current && flowRef.current.wsClient && typeof flowRef.current.wsClient.on === 'function'){
          try{
            flowRef.current.wsClient.on('open', ()=>{ setWsStatus('open'); console.log('WS open') })
            flowRef.current.wsClient.on('close', ()=>{ setWsStatus('closed'); console.log('WS closed') })
            flowRef.current.wsClient.on('error', (e)=>{ setWsStatus('error'); console.warn('WS error', e) })
          }catch(e){ console.warn('ws event register err', e) }
        }

        setPhase("listening")
        setSecondsLeft(duration)

        console.log('Step 5: starting streaming')
        startStreaming()
      }catch(flowErr){
        console.error('Flow start failed', flowErr)
        setWsStatus('error')
        setPhase('error')
      }

    } catch (err) {
      console.error("Start failed:", err)
      setPhase("error")
    }
  }

  // ⛔ STOP
  const stopInterview = async () => {
    stopStreaming()

    try {
      if (flowRef.current) {
        await flowRef.current.stop()
        flowRef.current = null
      }
    } catch (e) {
      console.warn("Flow stop error", e)
    }

    try {
      if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop())
        setMediaStream(null)
      }
    } catch (e) {}

    setPhase("idle")
  }

  // 🎨 UI
  return (
    <div className="interview-container">
      <WarningSystem alerts={alerts} />

      <div className="camera-panel camera-wrap">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-video"
        />

        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          style={{ display: "none" }}
        />

        <div className="camera-overlay">
          <div className="overlay-left">
            <div className="timer">{secondsLeft}s</div>
            <div className="progress" aria-hidden>
              <div className="progress-bar" style={{width: `${(secondsLeft/duration)*100}%`}} />
            </div>
          </div>

          <div className="overlay-right">
            <div>Phase: {phase}</div>
            <div>Cam: {cameraStatus}</div>
            <div>WS: {wsStatus}</div>
          </div>
        </div>

        <div className="camera-controls" style={{marginTop:12}}>
          <button className="btn" onClick={startInterview} disabled={phase !== 'idle'}>Start Interview</button>
          <button className="btn" style={{background:'#ef4444',color:'white'}} onClick={stopInterview}>Stop</button>
        </div>
      </div>

      <aside className="question-panel">
        <h3 className="question-title">Question</h3>
        <div className="question-text">{question}</div>

        <div className="answer-area">
          <textarea placeholder="Notes (optional)" />
        </div>

        <div className="question-actions">
          <div>Integrity Score: <strong>{integrityScore ?? '--'}</strong></div>
          <div>Alerts: {(alerts || []).length || 0}</div>
        </div>
      </aside>
    </div>
  )
}

// 🎨 Styles
// styles moved to index.css