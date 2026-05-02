import React from 'react'
import { Link } from 'react-router-dom'

export default function Sidebar(){
  return (
    <aside className="sidebar" style={{width:240,background:'#071029',padding:18,color:'#E6EEF8',borderRadius:12}}>
      <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:18}}>
        <div style={{width:44,height:44,borderRadius:8,background:'linear-gradient(135deg,var(--violet),var(--lav))',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:800,color:'#071022'}}>AI</div>
        <div>
          <div style={{fontWeight:800}}>VerifyAI</div>
          <div style={{fontSize:12,opacity:0.7}}>Answer Verification</div>
        </div>
      </div>

      <nav style={{display:'flex',flexDirection:'column',gap:10}}>
        <Link to="/dashboard" style={linkStyle}>Dashboard</Link>
        <Link to="/verifications" style={linkStyle}>Verifications</Link>
        <Link to="/upload" style={linkStyle}>Upload Answer</Link>
        <Link to="/analytics" style={linkStyle}>Analytics</Link>
        <Link to="/reports" style={linkStyle}>Reports</Link>
        <Link to="/settings" style={linkStyle}>Settings</Link>
      </nav>
    </aside>
  )
}

const linkStyle = {
  color: '#CFE6FF',
  textDecoration: 'none',
  padding: '8px 12px',
  borderRadius: 8,
  display: 'inline-block',
  fontWeight:700,
  background: 'transparent'
}
