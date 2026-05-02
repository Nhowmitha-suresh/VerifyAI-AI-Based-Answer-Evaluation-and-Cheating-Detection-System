import React, { useContext } from 'react'
import { AppDataContext } from '../App'
import { Line, Bar, Pie } from 'react-chartjs-2'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Tooltip, Legend } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Tooltip, Legend)

export default function Analytics(){
  const { resumeData } = useContext(AppDataContext)

  // build simple skills chart from resumeData.parsed.technologies or skills
  const techs = resumeData?.parsed?.technologies || []
  const skills = resumeData?.parsed?.skills || []
  const labels = (techs.length? techs : skills.length? skills : ['No data'])
  const values = labels.map((l,i)=> Math.max(20, 100 - i*10))

  const barData = { labels, datasets: [{ label:'Estimated Familiarity', data: values, backgroundColor: 'rgba(124,92,252,0.8)' }] }

  const lineData = {
    labels: ['Q1','Q2','Q3','Q4','Q5'],
    datasets: [{ label: 'Score Trend', data: [60,75,68,82,78], borderColor: '#C084FC', tension:0.4 }]
  }

  const pieData = {
    labels: ['Correct','Partial','Incorrect'],
    datasets: [{ data: [15,3,2], backgroundColor: ['#10b981','#f59e0b','#ef4444'] }]
  }

  return (
    <div style={{padding:20}}>
      <h2>Analytics</h2>
      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:16,marginTop:12}}>
        <div className="panel">
          <h3>Score Trend</h3>
          <div style={{height:240}}><Line data={lineData} /></div>
        </div>

        <div className="panel">
          <h3>Top Skills</h3>
          <div style={{height:240}}><Bar data={barData} /></div>
        </div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,marginTop:12}}>
        <div className="panel">
          <h3>Question Distribution</h3>
          <div style={{height:200}}><Pie data={pieData} /></div>
        </div>

        <div className="panel">
          <h3>Extracted Resume Sections</h3>
          <pre style={{whiteSpace:'pre-wrap',maxHeight:240,overflow:'auto'}}>{JSON.stringify(resumeData?.parsed || {}, null, 2)}</pre>
        </div>
      </div>
    </div>
  )
}
