import apiFetch from './api'
import { createWS } from './wsClient'

// InterviewFlow: central controller for session lifecycle, WS, uploads.
export class InterviewFlow {
  constructor(onEvent){
    this.onEvent = onEvent
    this.sessionId = null
    this.wsClient = null
    this.state = 'idle' // idle|starting|listening|analyzing|result|error
    this._uploading = false
  }

  async start(){
    if(this.state !== 'idle') throw new Error('flow must be idle to start')
    this._set('starting')
    try{
      const r = await apiFetch('/session/start', { method: 'POST' })
      this.sessionId = r.session_id
      // establish WS client
      this.wsClient = createWS(this.sessionId, msg => this._handleWS(msg))
      this._set('listening')
      return this.sessionId
    }catch(e){ this._set('error'); throw e }
  }

  async stop(){
    try{
      if(this.wsClient) this.wsClient.close()
      await apiFetch(`/session/end?sid=${this.sessionId}`, { method: 'POST' }).catch(()=>{})
    }catch(e){ console.warn('flow stop err', e) }
    this.sessionId = null
    this.wsClient = null
    this._set('idle')
  }

  _handleWS(msg){
    // proxy WS events to consumer
    this.onEvent && this.onEvent({ type: 'ws', msg })
  }

  sendFrame(arrayBuffer){
    try{
      if(!this.wsClient) return
      if(this.wsClient.ready !== WebSocket.OPEN) return
      this.wsClient.sendBinary(arrayBuffer)
    }catch(e){ console.warn('sendFrame err', e) }
  }

  async uploadAudio(blob, timeoutMs = 45000){
    if(!this.sessionId) throw new Error('no session')
    if(this._uploading) throw new Error('upload in progress')
    this._uploading = true
    this._set('analyzing')
    const form = new FormData(); form.append('file', blob, 'recording.webm')
    const controller = new AbortController()
    const timer = setTimeout(()=>controller.abort(), timeoutMs)
    try{
      const resp = await fetch(`${(import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000')}/audio/transcribe?session=${this.sessionId}`, { method: 'POST', body: form, signal: controller.signal })
      if(resp.status === 503){
        this._uploading = false
        clearTimeout(timer)
        this._set('listening')
        return { status: 'no-model' }
      }
      if(!resp.ok) throw new Error(await resp.text())
      const j = await resp.json()
      // call auth evaluate
      const ev = await apiFetch('/auth/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ transcript: j.transcript, duration_seconds: j.duration || 0 }) })
      this._uploading = false
      clearTimeout(timer)
      this._set('result')
      return { transcript: j.transcript, auth: ev }
    }catch(e){
      this._uploading = false
      clearTimeout(timer)
      this._set('error')
      throw e
    }
  }

  _set(s){ this.state = s; this.onEvent && this.onEvent({ type: 'phase', phase: s }) }
}

export default InterviewFlow
