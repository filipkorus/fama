import { useState } from 'react'
import './App.css'
import { useWebSocket } from './hooks/useWebSocket'

function App() {
  const { isConnected, sendMessage, messages, username, register } = useWebSocket()
  const [messageInput, setMessageInput] = useState('')
  const [usernameInput, setUsernameInput] = useState('')

  const handleSendMessage = () => {
    if (!messageInput.trim()) return

    sendMessage(messageInput)
    setMessageInput('')
  }

  const handleRegister = () => {
    if (!usernameInput.trim()) return

    register(usernameInput)
    setUsernameInput('')
  }

  return (
    <div className="app">
      <header>
        <h1>Post-Quantum Cryptography - WebSocket Demo</h1>
        <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </header>

      <main>
        {!username ? (
          <div className="chat-section">
            <h2>Register</h2>
            <div className="input-section">
              <input
                type="text"
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleRegister()}
                placeholder="Enter your username..."
              />
              <button onClick={handleRegister}>Register</button>
            </div>
          </div>
        ) : (
          <div className="chat-section">
            <p style={{ marginBottom: '20px' }}>Logged in as: <strong>{username}</strong></p>

            <div className="messages-list">
              {messages.map((msg, idx) => (
                <div key={idx} className="message">
                  {msg}
                </div>
              ))}
            </div>

            <div className="input-section">
              <input
                type="text"
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Type a message..."
              />
              <button onClick={handleSendMessage}>Send</button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App

