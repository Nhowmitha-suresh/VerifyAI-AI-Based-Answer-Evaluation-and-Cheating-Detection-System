import React, { useState, createContext } from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import { StatusBar } from 'react-native'
import HomeScreen from './screens/HomeScreen'
import AnalysisScreen from './screens/AnalysisScreen'
import ResultScreen from './screens/ResultScreen'
import HistoryScreen from './screens/HistoryScreen'

export const HistoryContext = createContext({})

const Stack = createNativeStackNavigator()

export default function App(){
  const [history, setHistory] = useState([])

  const addHistory = (entry) => setHistory(prev => [entry, ...prev])

  return (
    <HistoryContext.Provider value={{history, addHistory}}>
      <NavigationContainer>
        <StatusBar barStyle="light-content" backgroundColor="#0B0B0F" />
        <Stack.Navigator screenOptions={{ headerShown:false }}>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="Analysis" component={AnalysisScreen} />
          <Stack.Screen name="Result" component={ResultScreen} />
          <Stack.Screen name="History" component={HistoryScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </HistoryContext.Provider>
  )
}
