import React, { useRef, useEffect, useState } from 'react'

// InterviewScreen: split layout with live camera preview and question panel.
// Adds webcam capture + WebSocket streaming of JPEG frames to backend `/ws/stream`.
export default function InterviewScreen({ duration = 120, question = 'Explain the difference between TCP and UDP.' }){
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const intervalRef = useRef(null)

  const [stream, setStream] = useState(null)
  const [running, setRunning] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(duration)
  const [answerText, setAnswerText] = useState('')
  const [connected, setConnected] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [model, setModel] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [integrityScore, setIntegrityScore] = useState(null)
  const [faceModel, setFaceModel] = useState(null)
  const lastFaceSeenRef = useRef(0)

  // Start camera when component mounts
  useEffect(()=>{
    let mounted = true
    async function initCamera(){
      try{
        const s = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false })
        if(!mounted) return
        videoRef.current.srcObject = s
        setStream(s)
        // try to load COCO-SSD model from the page script (window.cocoSsd)
        try{
          if(window.cocoSsd && window.cocoSsd.load){
            const m = await window.cocoSsd.load()
            setModel(m)
            console.log('COCO-SSD model loaded')
          }
        }catch(err){ console.warn('coco-ssd load failed', err) }
        // load face-landmarks-detection (MediaPipe facemesh) if available
        try{
          if(window.faceLandmarksDetection && window.faceLandmarksDetection.load){
            // prefer MediaPipe FaceMesh via tfjs backend
            const fm = await window.faceLandmarksDetection.load(window.faceLandmarksDetection.SupportedPackages.mediapipeFacemesh)
            setFaceModel(fm)
            console.log('Face landmarks model loaded')
          }
        }catch(err){ console.warn('face landmarks load failed', err) }
      }catch(err){
        console.error('Camera error', err)
      }
    }
    initCamera()
    return ()=>{
      mounted = false
      stopStreaming()
      if(stream){
        stream.getTracks().forEach(t=>t.stop())
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Timer effect
  useEffect(()=>{
    if(!running) return
    if(secondsLeft <= 0){
      setRunning(false)
      return
    }
    const id = setInterval(()=>{
      setSecondsLeft(s=>s-1)
    }, 1000)
    return ()=>clearInterval(id)
  }, [running, secondsLeft])

  const startAnswer = ()=>{
    setSecondsLeft(duration)
    setRunning(true)
  }

  const stopAnswer = ()=>{
    setRunning(false)
  }

  // WebSocket connection
  const connectWS = ()=>{
    if(wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) return
    try{
      const ws = new WebSocket('ws://127.0.0.1:8000/ws/stream')
      ws.binaryType = 'arraybuffer'
      ws.onopen = ()=>{ setConnected(true); console.log('ws open') }
      ws.onmessage = (m)=>{
        try{
          const j = JSON.parse(m.data)
          // server alerts payload: {frame, alerts, integrity, faces}
          if(j.alerts){
            setAlerts(prev=>{
              // merge unique
              const merged = Array.from(new Set([...(prev||[]), ...j.alerts]))
              return merged
            })
          }
          if(typeof j.integrity !== 'undefined') setIntegrityScore(j.integrity)
          if(typeof j.faces !== 'undefined') console.debug('server faces:', j.faces)
        }catch(e){ console.log('ws msg', m.data) }
      }
      ws.onclose = ()=>{ setConnected(false); console.log('ws closed') }
      ws.onerror = (e)=>{ console.warn('ws error', e) }
      wsRef.current = ws
    }catch(err){ console.error('ws connect', err) }
  }

  // Start sending frames at ~5fps
  const startStreaming = ()=>{
    if(!videoRef.current || !videoRef.current.srcObject) return alert('Start camera first')
    connectWS()
    setStreaming(true)
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const sendFrame = async ()=>{
      if(!streaming) return
      try{
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
        canvas.toBlob(blob=>{
          if(blob && wsRef.current && wsRef.current.readyState === WebSocket.OPEN){
            blob.arrayBuffer().then(buf=>wsRef.current.send(buf))
          }
        }, 'image/jpeg', 0.6)
        // Run lightweight in-browser object detection if model is available
        if(model){
          model.detect(videoRef.current).then(predictions=>{
            const newAlerts = []
            let personCount = 0
            let phoneDetected = false
            predictions.forEach(p=>{
              const cls = p.class || p.className || p.label
              if(cls === 'person') personCount += 1
              if(cls === 'cell phone' || cls === 'mobile phone' || cls === 'phone') phoneDetected = true
            })
            console.debug('Model detect:', {personCount, phoneDetected, predictionsCount: predictions.length})
            if(personCount === 0) {
              // mark no face seen locally
              // handled below by timestamp logic
            }
            if(personCount > 1) newAlerts.push('multiple_faces')
            if(phoneDetected) newAlerts.push('phone_detected')
            // compute simple integrity: penalize multiple faces or phone
            let score = 100
            if(personCount > 1) score -= 40
            if(phoneDetected) score -= 50
            // Keep any existing face-model flags later
            setAlerts(prev=>{
              const merged = Array.from(new Set([...(prev||[]), ...newAlerts]))
              return merged
            })
            setIntegrityScore(score)
            // if critical alerts, send flagged frame to backend
            if(newAlerts.length){
              sendFlaggedFrame(newAlerts)
            }
            // update last face seen timestamp
            if(personCount > 0){
              lastFaceSeenRef.current = Date.now()
              // remove 'User not visible' alert if present
              setAlerts(prev=> (prev||[]).filter(a=> a !== 'User not visible'))
            }
          }).catch(e=>{ /* ignore detection errors */ })
        }

        // Run face landmarks for gaze tracking if model available
        if(faceModel){
          try{
            const faces = await faceModel.estimateFaces({input: videoRef.current, returnTensors: false, flipHorizontal: false})
            if(faces && faces.length){
              // basic gaze estimation using iris / eye landmarks if available
              const f = faces[0]
              // try to access keypoints for left/right iris or eye
              const keypoints = f.scaledMesh || f.keypoints || []
              if(keypoints && keypoints.length){
                // use eyeball corners approx indices from MediaPipe (33 left, 263 right, iris center around 468-473)
                // fallback: compute bounding box of eye region and compare iris center
                const leftIris = keypoints[468] || keypoints[473] || null
                const rightIris = keypoints[473] || keypoints[468] || null
                let gazeOff = false
                if(leftIris && rightIris){
                  // average iris x relative to face box
                  const avgIrisX = (leftIris[0] + rightIris[0]) / 2
                  const faceBox = f.boundingBox || null
                  if(faceBox && faceBox.topLeft && faceBox.bottomRight){
                    const left = faceBox.topLeft[0]
                    const right = faceBox.bottomRight[0]
                    const rel = (avgIrisX - left) / (right - left)
                    // if gaze is near edges (rel < 0.2 or > 0.8) consider off-screen
                    if(rel < 0.2 || rel > 0.8) gazeOff = true
                  }
                }
                if(gazeOff){
                  setAlerts(prev=>Array.from(new Set([...(prev||[]), 'Off-screen gaze detected'])))
                  setIntegrityScore(s=> (s===null? 80 : Math.max(0, s-20)))
                  sendFlaggedFrame(['Off-screen gaze detected'])
                }
              }
            }
          }catch(e){ console.warn('face landmarks detect error', e) }
        }
      }catch(e){ console.warn('frame capture error', e) }
    }
    // initial frame then interval (throttle to 1 fps)
    sendFrame()
    intervalRef.current = setInterval(()=>{
      // check for no-face timeout (2s)
      try{
        const last = lastFaceSeenRef.current || 0
        if(last && (Date.now() - last) > 2000){
          // user not visible
          setAlerts(prev=> Array.from(new Set([...(prev||[]), 'User not visible'])))
        }
      }catch(e){ }
      sendFrame()
    }, 1000)
  }

  const stopStreaming = ()=>{
    setStreaming(false)
    if(intervalRef.current){ clearInterval(intervalRef.current); intervalRef.current = null }
    if(wsRef.current){ try{ wsRef.current.close() }catch(e){} wsRef.current = null }
  }

  const toggleStream = ()=>{
    if(streaming) stopStreaming(); else startStreaming()
  }

  // Start full interview: start timer, streaming, recording and speech recog
  const startInterview = async ()=>{
    console.log('Starting interview')
    setAlerts([])
    try{
      // ensure microphone permission prompt early
      try{ await navigator.mediaDevices.getUserMedia({ audio: true, video: false }); }catch(e){ console.warn('mic permission prompt failed', e) }
    }catch(e){}
    startAnswer()
    startStreaming()
    startRecognition()
    startAudioRecording()
  }

  const stopInterview = ()=>{
    console.log('Stopping interview')
    stopRecognition()
    stopAudioRecording()
    stopStreaming()
    stopAnswer()
  }

  const submitAnswer = ()=>{
    // Placeholder: in real app, send the recorded answer / transcript to backend
    console.log('Submitting answer:', answerText)
    // send to backend NLP scorer for immediate feedback
    fetch('http://127.0.0.1:8000/nlp/score', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({question, answer: answerText, keywords: []})
    }).then(r=>r.json()).then(j=>{
      // show score and speak feedback
      const s = j.score || 0
      alert('Score: ' + s)
      const utter = new SpeechSynthesisUtterance(`Your score is ${Math.round(s)} points. Suggestions: ${Object.keys(j.details||{}).length? JSON.stringify(j.details): 'No details.'}`)
      speechSynthesis.cancel(); speechSynthesis.speak(utter)
    }).catch(err=>{ console.error('scoring error', err); alert('Score request failed') })
  }

  // Live speech recognition (Web Speech API) — append transcript to answerText
  const startRecognition = ()=>{
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if(!SpeechRecognition) return alert('SpeechRecognition not supported in this browser')
    const recog = new SpeechRecognition()
    recog.lang = 'en-US'
    recog.interimResults = true
    recog.continuous = true
    recog.onresult = (ev)=>{
      let interim = ''
      let final = ''
      for(let i=ev.resultIndex;i<ev.results.length;i++){
        const res = ev.results[i]
        if(res.isFinal) final += res[0].transcript + ' '
        else interim += res[0].transcript
      }
      if(final) setAnswerText(t=> (t ? t + ' ' : '') + final)
    }
    recog.onerror = (e)=>console.warn('recog error', e)
    recog.onend = ()=>console.log('recog ended')
    try{ recog.start(); window._activeRecog = recog }catch(e){console.warn(e)}
  }

  const stopRecognition = ()=>{
    try{ if(window._activeRecog) window._activeRecog.stop(); window._activeRecog = null }catch(e){ }
  }

  // send flagged frame (canvas image) to backend for logging and later review
  const sendFlaggedFrame = async (reasons=[])=>{
    try{
      const canvas = canvasRef.current
      if(!canvas) return
      const blob = await new Promise(res=>canvas.toBlob(res, 'image/jpeg', 0.8))
      const form = new FormData()
      form.append('file', blob, `flagged-${Date.now()}.jpg`)
      form.append('reasons', JSON.stringify(reasons))
      form.append('integrity', String(integrityScore||0))
      await fetch('http://127.0.0.1:8000/flagged-frame', { method: 'POST', body: form })
    }catch(e){ console.warn('sendFlaggedFrame err', e) }
  }

  const percent = Math.round(((duration - secondsLeft) / duration) * 100)

  // Audio recording (MediaRecorder)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioStreamRef = useRef(null)
  const [recording, setRecording] = useState(false)
  const [lastTranscript, setLastTranscript] = useState('')
  const [authResult, setAuthResult] = useState(null)

  const startAudioRecording = async ()=>{
    if(!stream){
      alert('Camera/audio not started')
      return
    }
    try{
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      audioStreamRef.current = micStream
      const mr = new MediaRecorder(micStream)
      audioChunksRef.current = []
      mr.ondataavailable = e=>{
        if(e.data && e.data.size>0){
          console.debug('audio chunk received size=', e.data.size)
          audioChunksRef.current.push(e.data)
        }
      }
      mr.onstop = async ()=>{
        console.log('MediaRecorder stopped, sending audio to server, chunks=', audioChunksRef.current.length)
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        // compute duration roughly via audio element
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audio.onloadedmetadata = async ()=>{
          const dur = audio.duration || 0
          console.log('Recorded duration (s)=', dur)
          // send to server for transcription
          const form = new FormData()
          form.append('file', blob, 'recording.webm')
          try{
            const resp = await fetch('http://127.0.0.1:8000/audio/transcribe', { method: 'POST', body: form })
            console.log('transcribe status', resp.status)
            const j = await resp.json()
            console.log('transcribe response', j)
            const transcript = j.transcript || ''
            setLastTranscript(transcript)
            // evaluate authenticity
            const evalResp = await fetch('http://127.0.0.1:8000/auth/evaluate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ transcript, duration_seconds: dur })})
            const ev = await evalResp.json()
            setAuthResult(ev)
            // speak brief feedback
            const s = ev.authenticity_score || 0
            const utter = new SpeechSynthesisUtterance(`Authenticity score ${Math.round(s)}. Suggestions: filler ratio ${ev.details.filler_ratio}.`)
            speechSynthesis.cancel(); speechSynthesis.speak(utter)
          }catch(e){ console.warn('transcription request failed', e) }
        }
      }
      mr.start()
      mediaRecorderRef.current = mr
      setRecording(true)
    }catch(e){ console.warn('recorder start error', e); alert('Microphone permission denied') }
  }

  const stopAudioRecording = ()=>{
    try{ 
      if(mediaRecorderRef.current){ 
        mediaRecorderRef.current.stop(); 
        mediaRecorderRef.current = null 
      }
      if(audioStreamRef.current){
        try{ audioStreamRef.current.getTracks().forEach(t=>t.stop()) }catch(e){}
        audioStreamRef.current = null
      }
    }catch(e){}
    setRecording(false)
  }

  return (
    <div className="interview-container">
      <div className="camera-panel card">
        <div className="camera-wrap">
          <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
          <canvas ref={canvasRef} width={640} height={480} style={{display:'none'}} />
          <div className="camera-overlay">
            <div className="overlay-left">
              <div className="timer">{new Date(secondsLeft * 1000).toISOString().substr(14,5)}</div>
              <div className="progress">
                <div className="progress-bar" style={{width: `${percent}%`}} />
              </div>
            </div>
            <div className="overlay-right">
              <div className="integrity">Integrity: <strong>—</strong></div>
              <div className="confidence">Confidence: <span className="chip">—</span></div>
            </div>
          </div>
        </div>
        <div className="camera-controls">
          <button className="btn" onClick={startInterview} disabled={running}>Start Interview</button>
          <button className="btn" onClick={stopInterview} disabled={!running}>Stop Interview</button>
          <div style={{marginLeft:12,color:'#9AA6B2'}}>WS: {connected? 'connected':'disconnected'} · Recording: {recording? 'yes':'no'}</div>
        </div>
      </div>

      <div className="question-panel card">
        <h3 className="question-title">Question</h3>
        <p className="question-text">{question}</p>

        <div style={{marginTop:8}}>
          <div style={{fontSize:13,color:'#9AA6B2'}}>Live transcript</div>
          <div style={{background:'#061018',padding:8,borderRadius:8,minHeight:60,color:'#E6EEF8'}}>{answerText || <span style={{color:'#57646a'}}>No speech detected yet.</span>}</div>
        </div>

        <div className="answer-area">
          <textarea value={answerText} onChange={e=>setAnswerText(e.target.value)} placeholder="Type your answer here or use voice..." />
        </div>

        <div className="question-actions">
          <button className="btn" onClick={submitAnswer}>Submit Answer</button>
          <div style={{marginLeft:'auto',color:'#9AA6B2'}}>Mode: Video · Text</div>
        </div>

        <div style={{marginTop:12}}>
          <div style={{fontSize:13,color:'#9AA6B2'}}>Alerts</div>
          <div style={{marginTop:6,display:'flex',flexDirection:'column',gap:6}}>
            <div style={{background:'rgba(255,255,255,0.02)',padding:8,borderRadius:8}}>Integrity Score: <strong>{integrityScore===null? '—' : integrityScore}</strong></div>
            {(alerts || []).length === 0 ? (
              <div style={{color:'#57646a'}}>No alerts</div>
            ) : (
              alerts.map((a,i)=>(<div key={i} style={{background:'#2b1116',padding:8,borderRadius:8}}>{a}</div>))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
