import { useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import { socket } from '../services/socket'

export default function Chat() {
    const navigate = useNavigate();
    const { isConnected, username } = useWebSocket();

    const handleLogout = () => {
        window.localStorage.removeItem('auth')
        window.localStorage.removeItem('username')
        window.localStorage.removeItem('authToken')
        try {
            // Make sure socket stops sending authenticated requests
            if (socket) {
                try {
                    ;(socket as any).auth = {}
                } catch (e) {
                    /* ignore */
                }
                if (socket.connected) socket.disconnect()
            }
        } catch (err) {
            console.warn('Error disconnecting socket on logout', err)
        }
        navigate('/')
    };

    return (
        <div className="page">
            <header className="topbar">
                <div className="brand">
                <span className="brand-accent">FAMA</span>
                <span className="brand-sub">– secure chat</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    {username && (
                        <div style={{ fontSize: '14px', color: '#999' }}>
                            Logged in as: <strong>{username}</strong>
                        </div>
                    )}
                    <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
                    {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                    </div>
                    <button 
                        onClick={handleLogout}
                        style={{
                            padding: '8px 16px',
                            backgroundColor: '#ff4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '14px'
                        }}
                    >
                        Logout
                    </button>
                </div>
            </header>
            <main className="chat-main">
                <h1 className="title">Chat Page</h1>
                <p className="subtitle">
                    This is where the chat interface will be implemented.
                </p>
            </main>
        </div>
    );
}