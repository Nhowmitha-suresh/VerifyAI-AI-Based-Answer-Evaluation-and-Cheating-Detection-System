import React, { useContext } from 'react'
import { UserContext } from '../App'

export default function Topbar(){
  const { user } = useContext(UserContext)
  return (
    <header className="topbar" style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'14px 20px',background:'transparent'}}>
      <div style={{display:'flex',alignItems:'center',gap:12}}>
        <div style={{width:36,height:36,borderRadius:8,background:'linear-gradient(135deg,var(--violet),var(--lav))',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:800,color:'#071022'}}>V</div>
        <div style={{fontWeight:800}}>VerifyAI</div>
      </div>

      <div style={{display:'flex',alignItems:'center',gap:12}}>
        <div style={{color:'#CFE6FF',fontWeight:700}}>{user ? (user.name || user.email) : 'Guest'}</div>
        <button className="btn">Get Started</button>
        <div style={{width:40,height:40,borderRadius:999,background:'#0b1220'}} />
      </div>
    </header>
  )
}
