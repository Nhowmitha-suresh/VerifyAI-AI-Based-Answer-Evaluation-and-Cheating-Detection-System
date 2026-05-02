import React from 'react'

export default function Settings(){
  return (
    <div style={{padding:20}}>
      <h2>Settings</h2>
      <div className="panel" style={{marginTop:12,padding:20}}>
        <label style={{display:'block',marginBottom:8}}>Profile Name</label>
        <input style={{padding:8,borderRadius:8,background:'#071017',border:'1px solid rgba(255,255,255,0.03)',color:'#E6EEF8'}} />
      </div>
    </div>
  )
}
