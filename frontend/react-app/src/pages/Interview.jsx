import React, { useContext, useEffect, useState, useRef } from 'react'
import { AppDataContext } from '../App'
import api from '../services/api'
import { useNavigate } from 'react-router-dom'

export default function InterviewPage(){
  const { resumeData } = useContext(AppDataContext)
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const videoRef = useRef(null)
  const [faceDetected, setFaceDetected] = useState(false)
  const navigate = useNavigate()

  useEffect(()=>{
    const load = async ()=>{
      setLoading(true)
      try{
        const res = await api.getQuestions(resumeData?.upload_id)
        const list = (res.resume_questions && res.resume_questions.length? res.resume_questions : (res.computer_networks||[]).slice(0,5))
        setQuestions(list)
        setAnswers(new Array(list.length).fill(''))
        setLoading(false)
      }catch(e){ console.error(e); setError('Failed to load questions'); setLoading(false) }
    }
    load()
  },[resumeData])

  useEffect(()=>{
    // start camera
    const start = async ()=>{
      try{
        const s = await navigator.mediaDevices.getUserMedia({ video: true, audio:false })
        if(videoRef.current){ videoRef.current.srcObject = s }
      }catch(e){ console.warn('camera', e) }
    }
    start()
    // simple mock face detection: check video playing
    const id = setInterval(()=>{
      if(!videoRef.current) return
      const playing = !!(videoRef.current.currentTime > 0 && !videoRef.current.paused && !videoRef.current.ended)
      setFaceDetected(playing)
    },800)
    return ()=> clearInterval(id)
  },[])

  const handleNext = ()=>{ if(index < questions.length - 1) setIndex(i=>i+1) }
  const handlePrev = ()=>{ if(index>0) setIndex(i=>i-1) }

  const handleChange = (v)=>{
    const copy = [...answers]; copy[index] = v; setAnswers(copy)
  }

  const handleSubmit = async ()=>{
    setLoading(true)
    try{
      await api.submitAnswers(resumeData?.upload_id, answers)
      setLoading(false)
      navigate('/reports')
    }catch(e){ console.error(e); setError('Submit failed'); setLoading(false) }
  }

  if(loading) return <div style={{padding:20}}>Loading...</div>
  if(error) return <div style={{padding:20,color:'red'}}>{error}</div>

  const q = questions[index]

  return (
    <div style={{display:'flex',gap:18,padding:20}}>
      <div style={{flex:2}}>
        <div className="panel" style={{padding:18}}>
          <h3>Question {index+1}</h3>
          <p style={{fontSize:18}}>{q.question || q}</p>
          <textarea value={answers[index]||''} onChange={e=>handleChange(e.target.value)} style={{width:'100%',height:140,marginTop:12,background:'#071017',color:'#E6EEF8',padding:12,borderRadius:8}} />

          <div style={{display:'flex',justifyContent:'space-between',marginTop:12}}>
            <div>
              <button className="btn" onClick={handlePrev} disabled={index===0}>Previous</button>
              <button className="btn" onClick={handleNext} style={{marginLeft:8}} disabled={index>=questions.length-1}>Next</button>
            </div>
            <div>
              <button className="btn" onClick={handleSubmit} disabled={loading}>{loading? 'Submitting...':'Submit Answers'}</button>
            </div>
          </div>
        </div>
      </div>

      <aside style={{width:360}}>
        <div className="panel" style={{padding:12}}>
          <h4>Live Proctoring</h4>
          <video ref={videoRef} autoPlay playsInline muted style={{width:'100%',borderRadius:8,background:'#000'}} />
          <div style={{marginTop:8}}>Face detected: <strong style={{color: faceDetected? '#34d399':'#ef4444'}}>{faceDetected? 'Yes':'No'}</strong></div>
        </div>
      </aside>
    </div>
  )
}
