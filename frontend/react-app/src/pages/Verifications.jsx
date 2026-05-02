import React from 'react'

export default function Verifications(){
  return (
    <div style={{padding:20}}>
      <h2>Verifications</h2>
      <div className="panel" style={{marginTop:12}}>
        <table style={{width:'100%'}}>
          <thead><tr><th>File</th><th>Score</th><th>Status</th></tr></thead>
          <tbody>
            <tr><td>answer_01.pdf</td><td>85%</td><td>Completed</td></tr>
            <tr><td>answer_02.pdf</td><td>72%</td><td>Completed</td></tr>
            <tr><td>answer_03.pdf</td><td>65%</td><td>In Progress</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
