import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import './App.css'
import { api } from './services/api'
import { socket } from './services/socket'
import Home from './pages/Home'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import Chat from './components/Chat'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  useEffect(() => {
    // On app start, if there's a stored token, attach it to API and socket so
    // refreshing the page preserves authenticated state for HTTP + Socket.IO.
    try {
      const token = typeof window !== 'undefined' ? window.localStorage.getItem('authToken') : null
      if (token) {
        try {
          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
        } catch (err) {
          console.warn('Failed to set default API authorization header', err)
        }

        try {
          const bearer = `Bearer ${token}`
          ;(socket as any).auth = { token: bearer }
          if (socket.connected) {
            socket.disconnect()
          }
          socket.connect()
        } catch (err) {
          console.warn('Failed to (re)connect socket with token', err)
        }
      }
    } catch (err) {
      console.warn('App initialization error', err)
    }
  }, [])
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route 
          path="/chat" 
          element={
            <ProtectedRoute>
              <Chat />
            </ProtectedRoute>
          } 
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App

