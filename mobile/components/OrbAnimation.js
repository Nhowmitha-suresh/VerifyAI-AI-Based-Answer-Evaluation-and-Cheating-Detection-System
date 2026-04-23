import React, { useEffect, useRef } from 'react'
import { Animated, View, StyleSheet, Easing } from 'react-native'
import LottieView from 'lottie-react-native'
import orbJson from '../assets/orb.json'

const GLOW_COLORS = {
  trusted: 'rgba(78,240,182,0.9)',
  suspicious: 'rgba(255,77,109,0.95)',
  mixed: 'rgba(255,200,87,0.92)'
}

export default function OrbAnimation({ state = 'idle', resultType = null, size = 180 }){
  const scale = useRef(new Animated.Value(1)).current
  const baseOpacity = useRef(new Animated.Value(1)).current
  const glowOpacity = useRef(new Animated.Value(0)).current
  const lottieRef = useRef(null)

  useEffect(()=>{
    let maxScale = 1.02
    let duration = 1200
    let targetOpacity = 0.98
    if(state === 'listening'){ maxScale = 1.06; duration = 900; targetOpacity = 1 }
    if(state === 'analyzing'){ maxScale = 1.12; duration = 700; targetOpacity = 1 }

    Animated.timing(baseOpacity, { toValue: targetOpacity, duration: 300, useNativeDriver: true }).start()

    const pulse = Animated.loop(Animated.sequence([
      Animated.timing(scale, { toValue: maxScale, duration, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(scale, { toValue: 1, duration, easing: Easing.inOut(Easing.ease), useNativeDriver: true })
    ]))
    pulse.start()

    const speed = state === 'listening' ? 1.3 : state === 'analyzing' ? 0.9 : 0.8
    try{ lottieRef.current && lottieRef.current.setSpeed && lottieRef.current.setSpeed(speed) }catch(e){}

    return ()=> pulse && pulse.stop()
  },[state])

  useEffect(()=>{
    if(!resultType){
      Animated.timing(glowOpacity, { toValue: 0, duration: 360, useNativeDriver: true }).start()
      return
    }
    Animated.timing(glowOpacity, { toValue: 0.42, duration: 420, easing: Easing.inOut(Easing.ease), useNativeDriver: true }).start()
  },[resultType])

  const glowColor = resultType ? (GLOW_COLORS[resultType] || GLOW_COLORS.mixed) : 'transparent'

  return (
    <View style={[styles.container, { width: size, height: size }] }>
      <Animated.View style={[styles.wrapper, { transform:[{ scale }], opacity: baseOpacity, width: size, height: size, borderRadius: size/2 }] }>
        <LottieView ref={lottieRef} source={orbJson} autoPlay loop style={{ width: size, height: size }} />
        <Animated.View pointerEvents="none" style={[styles.glow, { backgroundColor: glowColor, opacity: glowOpacity, borderRadius: size/2, width: size, height: size }]} />
      </Animated.View>
    </View>
  )
}

const styles = StyleSheet.create({
  container:{ alignItems:'center', justifyContent:'center' },
  wrapper:{ alignItems:'center', justifyContent:'center', backgroundColor:'transparent' },
  glow:{ position:'absolute', left:0, right:0, top:0, bottom:0, shadowColor:'#000', shadowOpacity:0.12, shadowRadius:20 }
})
