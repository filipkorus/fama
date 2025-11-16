import { useState } from 'react'
import './App.css'
import { useWebSocket } from './hooks/useWebSocket'
import Chat from './components/Chat'
import ContactList from './components/ContactList'
import { Box } from '@mui/material'
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom'

function RegisterPage() {
  const { isConnected, username, register } = useWebSocket()
  const [usernameInput, setUsernameInput] = useState('')
  const navigate = useNavigate()

  const handleRegister = () => {
    if (!usernameInput.trim()) return
    register(usernameInput)
    setUsernameInput('')
    setTimeout(() => navigate('/chat'), 300) // Give time for registration
  }

  return (
    <div
      className="app"
      style={{
        minHeight: '100vh',
        background: 'radial-gradient(ellipse at top, #2a003f 0%, #0a0015 100%)',
        color: '#fff',
        fontFamily: 'inherit',
      }}
    >
      <header style={{ textAlign: 'center', padding: '32px 0 0 0' }}>
        <h1 style={{ color: '#ff4fff', fontWeight: 700, letterSpacing: 2 }}>FAMA <span style={{ color: '#fff', fontWeight: 400, fontSize: '1.2rem' }}>– secure chat</span></h1>
        <div
          style={{
            display: 'inline-block',
            marginTop: 12,
            marginBottom: 24,
            padding: '4px 18px',
            borderRadius: 16,
            background: isConnected ? 'rgba(0,255,100,0.15)' : 'rgba(255,0,60,0.15)',
            color: isConnected ? '#00ff64' : '#ff4f4f',
            fontWeight: 600,
            fontSize: 16,
            border: `1px solid ${isConnected ? '#00ff64' : '#ff4f4f'}`,
          }}
        >
          {isConnected ? '● Connected' : '● Disconnected'}
        </div>
        <hr style={{ border: 'none', borderTop: '2px solid #2a003f', margin: '24px auto 0 auto', width: 480, maxWidth: '90%' }} />
      </header>

      <main style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', minHeight: '70vh', marginTop: 32 }}>
        {!username ? (
          <div
            style={{
              background: 'rgba(20,0,30,0.95)',
              borderRadius: 16,
              boxShadow: '0 0 40px #a020f0',
              padding: '40px 32px',
              minWidth: 340,
              margin: '0 auto',
            }}
          >
            <h2 style={{ color: '#ff4fff', fontWeight: 700, textAlign: 'center', marginBottom: 24 }}>Register</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <label style={{ color: '#fff', fontWeight: 500, marginBottom: 4 }}>Username:</label>
              <input
                type="text"
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleRegister()}
                placeholder="Enter your username..."
                style={{
                  padding: '10px 14px',
                  borderRadius: 8,
                  border: '1px solid #a020f0',
                  background: 'rgba(30,0,40,0.8)',
                  color: '#fff',
                  fontSize: 16,
                  outline: 'none',
                  marginBottom: 16,
                }}
              />
              <button
                onClick={handleRegister}
                style={{
                  background: 'linear-gradient(90deg, #a020f0 0%, #ff4fff 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 8,
                  padding: '10px 0',
                  fontWeight: 700,
                  fontSize: 18,
                  cursor: 'pointer',
                  boxShadow: '0 0 10px #a020f0',
                }}
              >
                Register
              </button>
            </div>
          </div>
        ) : (
          <Box sx={{ display: 'flex', gap: 4, width: '100%', justifyContent: 'center' }}>
            <Chat />
          </Box>
        )}
      </main>
    </div>
  )
}

function ChatPage() {
  return <Chat />
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<RegisterPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  )
}

export default App

