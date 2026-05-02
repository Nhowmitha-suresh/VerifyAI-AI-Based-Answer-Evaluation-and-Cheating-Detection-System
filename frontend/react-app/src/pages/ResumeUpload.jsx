import React, { useRef, useState, useContext } from 'react'
import { AppDataContext } from '../App'
import api from '../services/api'
import { useNavigate } from 'react-router-dom'

export default function ResumeUpload(){
  const fileRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { setResumeData } = useContext(AppDataContext)
  const navigate = useNavigate()

  const onBrowse = ()=> fileRef.current && fileRef.current.click()

  const onFile = async (e) => {
    const file = e.target.files && e.target.files[0]
    if(!file) return
    setError('')
    setLoading(true)
    try{
      const json = await api.uploadResumeFile(file)
      // store upload_id and basics
      setResumeData({ upload_id: json.upload_id, name: json.name, skills: json.skills, experience: json.experience })
      setLoading(false)
      navigate('/interview')
    }catch(err){
      console.error(err)
      setError('Upload failed')
      setLoading(false)
    }
  }

  const dropHandler = async (ev) => {
    ev.preventDefault()
    const f = ev.dataTransfer.files && ev.dataTransfer.files[0]
    if(f){
      const fake = { target: { files: [f] } }
      await onFile(fake)
    }
  }

  return (
    <div style={{padding:20}}>
      <h2>Upload Resume</h2>
      <div className="panel" style={{marginTop:12,padding:24,display:'flex',flexDirection:'column',gap:12}}>
        <input type="file" ref={fileRef} onChange={onFile} accept=".pdf,.docx,.txt" style={{display:'none'}} />
        <div onDrop={dropHandler} onDragOver={e=>e.preventDefault()} style={{border:'2px dashed rgba(255,255,255,0.04)',padding:24,borderRadius:8,textAlign:'center',cursor:'pointer'}}>
          Drag & drop your file here<br/><small>PDF, DOCX, TXT</small>
        </div>
        <div style={{display:'flex',gap:12,alignItems:'center'}}>
          <button className="btn" onClick={onBrowse} disabled={loading}>{loading? 'Uploading...':'Upload Resume'}</button>
          {loading && <div style={{opacity:0.8}}>Uploading...</div>}
          {error && <div style={{color:'#ff6b6b'}}>{error}</div>}
        </div>
      </div>
    </div>
  )
}
