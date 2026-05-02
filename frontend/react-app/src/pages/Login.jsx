import React, { useContext, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { UserContext } from '../App'

export default function Login(){
  const { setUser } = useContext(UserContext)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const submit = (e)=>{
    e.preventDefault()
    // simple client-side mock login
    setUser({ email })
    navigate('/dashboard')
  }

  return (
    <div style={{display:'flex',alignItems:'center',justifyContent:'center',height:'100vh'}}>
      <form onSubmit={submit} style={{width:420,background:'linear-gradient(180deg,rgba(255,255,255,0.02),transparent)',padding:24,borderRadius:12}}>
        <h2>Welcome Back</h2>
        <label style={{display:'block',marginTop:12}}>Email</label>
        <input value={email} onChange={e=>setEmail(e.target.value)} style={{width:'100%',padding:10,borderRadius:8,background:'#071017',border:'1px solid rgba(255,255,255,0.03)',color:'#E6EEF8'}} />
        <label style={{display:'block',marginTop:12}}>Password</label>
        <input type="password" value={password} onChange={e=>setPassword(e.target.value)} style={{width:'100%',padding:10,borderRadius:8,background:'#071017',border:'1px solid rgba(255,255,255,0.03)',color:'#E6EEF8'}} />

        <div style={{marginTop:16,display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <button className="btn" style={{padding:'10px 18px'}}>Log in</button>
          <Link to="/signup" style={{color:'#CFE6FF'}}>Sign up</Link>
        </div>
      </form>
    </div>
  )
}
