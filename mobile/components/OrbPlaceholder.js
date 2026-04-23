import React, { useEffect, useRef } from 'react'
import { Animated, View, StyleSheet } from 'react-native'
import { THEME } from '../constants'

export default function OrbPlaceholder({ state='idle', size=160 }){
  const scale = useRef(new Animated.Value(1)).current

  useEffect(()=>{
    let anim
    if(state==='listening'){
      anim = Animated.loop(Animated.sequence([
        Animated.timing(scale,{toValue:1.06,duration:600,useNativeDriver:true}),
        Animated.timing(scale,{toValue:1.0,duration:600,useNativeDriver:true})
      ]))
      anim.start()
    } else if(state==='analyzing'){
      anim = Animated.loop(Animated.sequence([
        Animated.timing(scale,{toValue:1.02,duration:900,useNativeDriver:true}),
        Animated.timing(scale,{toValue:0.98,duration:900,useNativeDriver:true})
      ]))
      anim.start()
    } else {
      Animated.timing(scale,{toValue:1,duration:200,useNativeDriver:true}).start()
    }
    return ()=> anim && anim.stop()
  },[state])

  return (
    <Animated.View style={[styles.orb, { width:size, height:size, borderRadius:size/2, transform:[{scale}] }] }>
      <View style={styles.core} />
    </Animated.View>
  )
}

const styles = StyleSheet.create({
  orb:{
    backgroundColor: 'rgba(30,144,255,0.07)',
    alignItems:'center',
    justifyContent:'center',
    shadowColor: THEME.primary,
    shadowOpacity: 0.3,
    shadowRadius: 30,
    shadowOffset:{width:0,height:6}
  },
  core:{
    width: sizeCalc(64),
    height: sizeCalc(64),
    borderRadius: sizeCalc(32),
    backgroundColor: THEME.primary
  }
})

function sizeCalc(v){ return v }
