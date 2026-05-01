import React, { useEffect, useRef, useState } from 'react'

export default function WarningSystem({ alerts = [] }){
  const [warning, setWarning] = useState(false)
  const cooldownRef = useRef(false)
  const timerRef = useRef(null)
  const alarmRef = useRef(null)

  useEffect(()=>{
    if(!alerts || alerts.length === 0){
      setWarning(false)
      return
    }
    if(cooldownRef.current) return
    setWarning(true)
    cooldownRef.current = true

    if(!alarmRef.current){
      alarmRef.current = new Audio('https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg')
      alarmRef.current.preload = 'auto'
    }
    try{
      const p = alarmRef.current.play()
      if(p && p.catch) p.catch(()=>{})
    }catch(e){}

    if(timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(()=>{
      setWarning(false)
      // cooldown window
      setTimeout(()=>{ cooldownRef.current = false }, 2000)
    }, 2000)

    return ()=>{ if(timerRef.current) clearTimeout(timerRef.current) }
  }, [alerts])

  if(!warning) return null

  return (
    <>
      <style>{`@keyframes verifBlink{0%{opacity:0}50%{opacity:.6}100%{opacity:0}}`}</style>
      <div style={styles.overlay} aria-hidden />
      <div style={styles.banner}>⚠️ Warning: Suspicious activity detected — {alerts.join(', ')}</div>
    </>
  )
}

const styles = {
  overlay: {
    position:'fixed', top:0, left:0, width:'100%', height:'100%', background:'rgba(255,0,0,0.12)', pointerEvents:'none', zIndex:999, animation:'verifBlink 0.6s ease-in-out infinite'
  },
  banner: {
    position:'fixed', top:20, left:'50%', transform:'translateX(-50%)', background:'#b91c1c', color:'white', fontWeight:700, padding:'10px 18px', borderRadius:8, zIndex:1000, pointerEvents:'none'
  }
}
