import React from 'react'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

export default function Layout({ children }){
  return (
    <div style={{display:'flex',height:'100vh',gap:18,background:'linear-gradient(180deg,var(--bg),#06070a)',padding:18}}>
      <Sidebar />
      <div style={{flex:1,display:'flex',flexDirection:'column',gap:12}}>
        <Topbar />
        <main style={{flex:1,overflow:'auto'}}>
          {children}
        </main>
      </div>
    </div>
  )
}
