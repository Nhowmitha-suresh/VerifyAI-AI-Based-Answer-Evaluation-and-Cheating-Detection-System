import React from 'react'
import { View, Text, StyleSheet, TouchableOpacity, Share } from 'react-native'
import { THEME } from '../constants'
import OrbAnimation from '../components/OrbAnimation'
import ScoreDisplay from '../components/ScoreDisplay'

export default function ResultScreen({ route, navigation }){
  const { result, text } = route.params || { result: { score:0, highlights:[], explanation:'' }, text: '' }

  async function onShare(){
    try{
      await Share.share({ message: `VerifyAI: ${result.score}% — ${result.explanation}` })
    }catch(e){ console.warn(e) }
  }

  // determine resultType from score
  const getResultType = (score) => {
    if (typeof score !== 'number') return null
    if (score > 70) return 'trusted'
    if (score < 40) return 'suspicious'
    return 'mixed'
  }

  const getMessage = (type) => {
    if (type === 'trusted') return 'Seems reliable'
    if (type === 'suspicious') return 'Something feels off'
    return 'Needs more context'
  }

  const resultType = getResultType(result.score)
  const resultMessage = getMessage(resultType)

  return (
    <View style={styles.container}>
      <View style={styles.center}>
        <OrbAnimation state={'idle'} resultType={resultType} />
        <Text style={styles.message}>{resultMessage}</Text>
        <ScoreDisplay score={result.score} resultType={resultType} />
        <View style={styles.tagsRow}>
          <View style={styles.tag}><Text style={styles.tagText}>Misleading</Text></View>
          <View style={styles.tag}><Text style={styles.tagText}>Biased</Text></View>
          <View style={styles.tag}><Text style={styles.tagText}>Lacks context</Text></View>
        </View>

        <View style={styles.card}><Text style={{color:'#E6EEF8'}}>{result.explanation}</Text></View>

        <View style={styles.actions}>
          <TouchableOpacity style={styles.primary} onPress={onShare}><Text style={styles.primaryText}>Share Result</Text></TouchableOpacity>
          <TouchableOpacity style={styles.ghost} onPress={()=>navigation.navigate('Home')}><Text style={{color:THEME.primary}}>Analyze Again</Text></TouchableOpacity>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor: THEME.background },
  center:{ alignItems:'center', paddingTop:80 },
  score:{ fontSize:64, color: THEME.primary, fontWeight:'800' },
  message:{ color: THEME.muted, marginTop:8, marginBottom:6, fontSize:16 },
  tagsRow:{ flexDirection:'row', marginTop:14 },
  tag:{ backgroundColor: 'rgba(255,255,255,0.02)', padding:8, borderRadius:10, marginHorizontal:6, marginRight:8 },
  tagText:{ color:'#E6EEF8' },
  card:{ marginTop:20, width:'90%', padding:14, backgroundColor: THEME.card, borderRadius:12 },
  actions:{ flexDirection:'row', marginTop:24 },
  primary:{ backgroundColor: THEME.primary, padding:12, borderRadius:12, marginRight:12 },
  primaryText:{ color:'#071022', fontWeight:'700' },
  ghost:{ padding:12, borderRadius:12 }
})
