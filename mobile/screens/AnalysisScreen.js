import React, { useEffect, useState, useContext } from 'react'
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, TouchableOpacity } from 'react-native'
import { analyzeText } from '../services/api'
import { THEME } from '../constants'
import { HistoryContext } from '../App'

export default function AnalysisScreen({ route, navigation }){
  const { input } = route.params || { input: '' }
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const { addHistory } = useContext(HistoryContext)

  useEffect(()=>{
    setLoading(true)
    analyzeText(input).then(res=>{
      setResult(res)
      setLoading(false)
      addHistory({ score: res.score, text: input, time: new Date().toISOString(), tags: res.highlights.filter(h=>h.type==='suspicious').slice(0,3).map(h=>h.word) })
      // navigate to result after a small pause
      setTimeout(()=> navigation.navigate('Result', { result: res, text: input }), 600)
    })
  },[])

  function renderHighlighted(){
    if(!result) return null
    const map = {}
    result.highlights.forEach(h=>{ map[h.word] = h.type })
    const words = input.split(/(\s+)/)
    return words.map((w,idx)=>{
      const t = map[w.trim()]
      const cls = t==='suspicious'? styles.red : t==='unclear'? styles.yellow : t==='verified'? styles.green : null
      return (<Text key={idx} style={[styles.word, cls]}>{w}</Text>)
    })
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}><Text style={styles.title}>Analyzing</Text></View>
      <ScrollView style={styles.card} contentContainerStyle={{padding:16}}>
        {loading ? (
          <View style={{alignItems:'center',padding:40}}>
            <ActivityIndicator size="large" color={THEME.primary} />
            <Text style={{color:THEME.muted,marginTop:12}}>Checking sources and context…</Text>
          </View>
        ) : (
          <View style={{flexWrap:'wrap',flexDirection:'row'}}>{renderHighlighted()}</View>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor: THEME.background },
  header:{ paddingTop:40, paddingHorizontal:20 },
  title:{ color:'#E6EEF8', fontSize:20, fontWeight:'700' },
  card:{ margin:16, backgroundColor: THEME.card, borderRadius:14 },
  word:{ fontSize:16, color:'#E6EEF8' },
  red:{ backgroundColor: 'rgba(255,77,109,0.06)', padding:4, borderRadius:6, margin:2 },
  yellow:{ backgroundColor: 'rgba(255,200,87,0.06)', padding:4, borderRadius:6, margin:2 },
  green:{ backgroundColor: 'rgba(78,240,182,0.06)', padding:4, borderRadius:6, margin:2 }
})
