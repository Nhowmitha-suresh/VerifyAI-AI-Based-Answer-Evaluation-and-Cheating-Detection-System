import React, { useState, useEffect, useRef } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, Animated, Platform } from 'react-native'
import OrbAnimation from '../components/OrbAnimation'
import { THEME } from '../constants'
import { LinearGradient } from 'expo-linear-gradient'

export default function HomeScreen({ navigation }){
  const [state, setState] = useState('idle')
  const titleScale = useRef(new Animated.Value(0.96)).current

  useEffect(()=>{
    Animated.sequence([
      Animated.timing(titleScale,{ toValue: 1.03, duration: 380, useNativeDriver: true }),
      Animated.timing(titleScale,{ toValue: 1, duration: 220, useNativeDriver: true })
    ]).start()
  },[])

  function onMic(){
    setState('listening')
    setTimeout(()=>{
      // mock captured text and navigate
      const sample = 'Studies always show that this works in all cases'
      navigation.navigate('Analysis', { input: sample })
      setState('analyzing')
    }, 1200)
  }

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient colors={["#07070a", "#0F1116"]} style={styles.topBanner} start={[0,0]} end={[1,0]}>
        <Text style={styles.bannerText}>Verify before you trust</Text>
        <View style={styles.pills}>
          <TouchableOpacity style={styles.pill}><Text style={styles.pillText}>Paste Text</Text></TouchableOpacity>
          <TouchableOpacity style={styles.pill}><Text style={styles.pillText}>Upload Screenshot</Text></TouchableOpacity>
        </View>
      </LinearGradient>
      <Animated.View style={[styles.header, { transform:[{scale: titleScale}] }] }>
        <Text style={styles.appName}>VerifyAI</Text>
      </Animated.View>

      <View style={styles.center}>
        <OrbAnimation state={state} size={220} />
        <Text style={styles.hint}>Tap to verify</Text>
      </View>

      <View style={styles.footerRow}>
        <TouchableOpacity style={styles.upload} onPress={()=>navigation.navigate('Analysis',{ input: 'Pasted: Vaccines always cause X' })}>
          <Text style={styles.uploadText}>Paste / Upload</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.micButton} onPress={onMic}>
          <View style={styles.micCore} />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor: THEME.background, padding:20, justifyContent:'space-between' },
  header:{ alignItems:'flex-start', paddingTop:18, paddingHorizontal:6 },
  appName:{ color:'#E6EEF8', fontSize:20, fontWeight:'800', letterSpacing:0.6 },
  center:{ alignItems:'center', marginTop:80 },
  hint:{ color: THEME.muted, marginTop:18, fontSize:16 },
  footerRow:{ flexDirection:'row', alignItems:'center', justifyContent:'space-between', padding:20 },
  upload:{ paddingVertical:12, paddingHorizontal:14, backgroundColor: THEME.card, borderRadius:12 },
  uploadText:{ color:'#E6EEF8' },
  micButton:{ width:88, height:88, borderRadius:44, backgroundColor: THEME.card, alignItems:'center', justifyContent:'center' },
  micCore:{ width:46, height:46, borderRadius:23, backgroundColor: THEME.primary }
})

// Banner styles appended
const bannerStyles = StyleSheet.create({
  topBanner: {
    width: '100%',
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 12,
    marginBottom: 6,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  bannerText: {
    color: '#E6EEF8',
    fontSize: 16,
    fontWeight: '700',
    marginRight: 12,
  },
  pills: {
    flexDirection: 'row',
    alignItems: 'center'
  },
  pill: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
    marginLeft: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    ...Platform.select({ ios: { shadowColor: '#0cf', shadowOpacity: 0.08, shadowRadius: 8, shadowOffset: { width:0, height:4 } }, android: { elevation: 2 } })
  },
  pillText: { color: '#E6EEF8', fontSize: 13, fontWeight: '600' }
})

// Merge banner styles into main styles for simplicity in this file
Object.assign(styles, bannerStyles)

