import React from 'react'

export default function Dashboard(){
  return (
    <div style={{padding:20}}>
      <h2>Dashboard</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:16,marginTop:12}}>
        <div className="panel">Total Interviews<br/><strong>128</strong></div>
        <div className="panel">Average Score<br/><strong>78.5%</strong></div>
        <div className="panel">Alerts<br/><strong>24</strong></div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:16,marginTop:18}}>
        <div className="panel">
          <h3>Recent Verifications</h3>
          <ul>
            <li>answer_01.pdf — <strong>85%</strong></li>
            <li>answer_02.pdf — <strong>72%</strong></li>
            <li>answer_03.pdf — <strong>65%</strong></li>
          </ul>
        </div>

        <div className="panel">
          <h3>Risk Distribution</h3>
          <div style={{height:140,display:'flex',alignItems:'center',justifyContent:'center'}}>[Chart]</div>
        </div>
      </div>
    </div>
  )
}
