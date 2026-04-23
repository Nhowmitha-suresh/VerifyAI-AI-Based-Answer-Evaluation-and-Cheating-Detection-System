import React, { useContext } from 'react'
import { View, Text, StyleSheet, FlatList } from 'react-native'
import { HistoryContext } from '../App'
import { THEME } from '../constants'

export default function HistoryScreen(){
  const { history } = useContext(HistoryContext)

  return (
    <View style={styles.container}>
      <Text style={styles.title}>History</Text>
      <FlatList data={history} keyExtractor={(i,idx)=>idx.toString()} renderItem={({item})=> (
        <View style={styles.item}>
          <View style={styles.miniOrb} />
          <View style={{flex:1}}>
            <Text style={{color:'#E6EEF8',fontWeight:'700'}}>{item.score}%</Text>
            <Text style={{color:THEME.muted,fontSize:12}} numberOfLines={1}>{item.text}</Text>
          </View>
          <Text style={{color:THEME.muted,fontSize:12}}>{new Date(item.time).toLocaleString()}</Text>
        </View>
      )} />
    </View>
  )
}

const styles = StyleSheet.create({
  container:{ flex:1, backgroundColor: THEME.background, padding:16 },
  title:{ color:'#E6EEF8', fontSize:20, fontWeight:'700', marginBottom:12 },
  item:{ flexDirection:'row', alignItems:'center', padding:12, backgroundColor: THEME.card, borderRadius:12, marginBottom:10 },
  miniOrb:{ width:36, height:36, borderRadius:18, backgroundColor:'rgba(30,144,255,0.12)', marginRight:8 }
})
