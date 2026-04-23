import React, { useEffect, useRef } from 'react'
import { Animated, Text, StyleSheet, Easing } from 'react-native'
import { THEME } from '../constants'

const COLOR_MAP = {
  trusted: '#4EF0B6',
  suspicious: '#FF4D6D',
  mixed: '#FFC857'
}

export default function ScoreDisplay({ score = 0, resultType = 'mixed' }){
  const scale = useRef(new Animated.Value(0.8)).current
  const pulse = useRef(null)

  useEffect(()=>{
    // entry pop: 0.8 -> 1.1 -> 1
    Animated.sequence([
      Animated.timing(scale, { toValue: 1.1, duration: 300, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(scale, { toValue: 1.0, duration: 180, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]).start(() => {
      // subtle continuous pulse
      pulse.current = Animated.loop(
        Animated.sequence([
          Animated.timing(scale, { toValue: 1.05, duration: 1600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
          Animated.timing(scale, { toValue: 1.0, duration: 1600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        ])
      )
      // Animated.Easing might not be available; the easing function is optional
      try{ pulse.current.start() }catch(e){}
    })

    return ()=>{ if(pulse.current) pulse.current.stop() }
  },[])

  const color = COLOR_MAP[resultType] || COLOR_MAP.mixed

  return (
    <Animated.Text style={[styles.score, { transform: [{ scale }], color } ]}>
      {Math.round(score)}%
    </Animated.Text>
  )
}

const styles = StyleSheet.create({
  score: {
    fontSize: 64,
    fontWeight: '800',
    textAlign: 'center'
  }
})
