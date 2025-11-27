import { useNavigate } from 'react-router-dom'
import { logout } from '../services/auth'
import '../styles.css'

export default function LandingPage() {
    const navigate = useNavigate();

    const handleLogout = () => {
        logout()
        navigate('/')
    };

    return (
        <div className="page">
            <header className="topbar">
                <div className="brand">
                <span className="brand-accent">FAMA</span>
                <span className="brand-sub">– secure chat</span>
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
