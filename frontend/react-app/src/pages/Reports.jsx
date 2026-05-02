import React, { useContext, useEffect, useState } from 'react'
import { AppDataContext } from '../App'
import api from '../services/api'

export default function Reports(){
  const { resumeData } = useContext(AppDataContext)
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(()=>{
    const load = async ()=>{
      if(!resumeData?.upload_id) return
      setLoading(true)
      try{
        const r = await api.getReport(resumeData.upload_id)
        setReport(r)
        setLoading(false)
      }catch(e){ console.error(e); setError('Failed to load report'); setLoading(false) }
    }
    load()
  },[resumeData])

  if(!resumeData) return <div style={{padding:20}}>No resume uploaded yet.</div>
  if(loading) return <div style={{padding:20}}>Loading report...</div>
  if(error) return <div style={{padding:20,color:'red'}}>{error}</div>

  return (
    <div className="report-page" style={{padding:20}}>
      <div style={{display:'flex',gap:18}}>
        <div className="panel" style={{flex:1,padding:18}}>
          <h3>{resumeData.name}</h3>
          <div style={{opacity:0.8}}>Skills: {(resumeData.skills||[]).join(', ')}</div>
          <div style={{marginTop:12}}>Experience: {resumeData.experience}</div>
        </div>

        <div className="panel" style={{width:360,padding:18}}>
          <h4>Results</h4>
          {report? (
            <div>
              <div>Score: <strong>{report.score}</strong></div>
              <div>Integrity: <strong>{report.integrity}</strong></div>
              <div>Risk Level: <strong>{report.risk}</strong></div>
            </div>
          ) : <div>No report available</div>}
        </div>
      </div>
    </div>
  )
}
