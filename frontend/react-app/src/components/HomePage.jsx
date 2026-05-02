import React, { useEffect, useState } from "react"

import { useNavigate } from 'react-router-dom'

export default function HomePage() {
  const [glow, setGlow] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const interval = setInterval(() => setGlow(g => !g), 1200)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="home-screen" style={{height:'100vh',display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div className="panel" style={{maxWidth:900,padding:36,display:'flex',gap:24,alignItems:'center'}}>

        <div style={{flex:1}}>
          <h1 style={{fontSize:42,margin:0,fontFamily:'Syne, sans-serif'}}>Verify Answers. Detect Cheating.</h1>
          <p style={{opacity:0.75,marginTop:8}}>Advanced AI evaluation system to ensure academic integrity and promote honest learning.</p>

          <div style={{marginTop:22,display:'flex',gap:12}}>
            <button className="btn" onClick={()=>navigate('/login')}>Get Started</button>
            <button className="btn" style={{background:'transparent',color:'#CFE6FF',border:'1px solid rgba(255,255,255,0.04)'}}>Watch Demo</button>
          </div>
        </div>

        <div style={{width:220,display:'flex',flexDirection:'column',alignItems:'center'}}>
          <div style={{width:160,height:160,borderRadius:999,background:'radial-gradient(circle,#6366f1,#1e1b4b)',boxShadow: glow? '0 0 80px #6366f1':'0 0 30px #6366f1',transition:'all .8s'}} />
          <div style={{marginTop:12,opacity:.7,fontSize:14}}>AI Evaluation • Cheating Detection • Smart Analytics</div>
        </div>

      </div>
    </div>
  )
}
