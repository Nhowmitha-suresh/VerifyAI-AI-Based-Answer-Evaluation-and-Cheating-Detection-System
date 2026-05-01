import React, { useState } from "react"
import HomePage from "./components/HomePage"
import InterviewScreen from "./components/InterviewScreen"

function App() {
  const [started, setStarted] = useState(false)

  return started
    ? <InterviewScreen />
    : <HomePage onStart={() => setStarted(true)} />
}

export default App