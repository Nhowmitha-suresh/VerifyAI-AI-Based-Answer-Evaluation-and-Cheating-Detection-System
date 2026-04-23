import React from 'react'
import InterviewScreen from './components/InterviewScreen'

export default function App(){
  return (
    <div className="app">
      <div style={{padding:12,display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        <div style={{fontWeight:700}}>verifAI Pro</div>
        <div style={{color:'#9AA6B2'}}>Interview • Mock • Demo</div>
      </div>
      <InterviewScreen duration={150} />
    </div>
  )
}
