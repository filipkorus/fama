import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import './App.css'
import { initializeAuth, getStoredToken } from './services/auth'
import Home from './pages/Home'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import ChatPage from './pages/Chat'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  useEffect(() => {
    const token = getStoredToken()
    if (token) {
      initializeAuth(token).catch((err) => {
        console.warn('Failed to initialize auth on app start:', err)
      })
    }
  }, [])
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/chat/:contactId"
          element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App

