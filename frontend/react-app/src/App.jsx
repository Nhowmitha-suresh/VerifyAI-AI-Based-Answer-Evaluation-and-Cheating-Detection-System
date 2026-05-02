import React, { createContext, useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import HomePage from "./components/HomePage"
import InterviewScreen from "./components/InterviewScreen"
import InterviewPage from "./pages/Interview"
import Layout from "./components/Layout"
import Dashboard from "./pages/Dashboard"
import Reports from "./pages/Reports"
import Analytics from "./pages/Analytics"
import Verifications from "./pages/Verifications"
import Upload from "./pages/Upload"
import Settings from "./pages/Settings"
import Login from "./pages/Login"
import Signup from "./pages/Signup"

export const UserContext = createContext(null)
export const AppDataContext = createContext({ resumeData: null, setResumeData: ()=>{} })

function App(){
  const [user, setUser] = useState(null)

  const [resumeData, setResumeData] = useState(null)

  return (
    <UserContext.Provider value={{ user, setUser }}>
      <AppDataContext.Provider value={{ resumeData, setResumeData }}>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<HomePage />} />

              <Route path="/upload" element={<Layout><ResumeUpload /></Layout>} />
              <Route path="/interview" element={<Layout><Interview /></Layout>} />
              <Route path="/reports" element={<Layout><Reports /></Layout>} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
      </AppDataContext.Provider>
    </UserContext.Provider>
  )
}

export default App