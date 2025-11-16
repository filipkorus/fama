import { useNavigate } from 'react-router-dom';
import '../styles.css';
import { useWebSocket } from '../hooks/useWebSocket';

export default function Home() {
  const navigate = useNavigate();
  const { isConnected } = useWebSocket();
  
  // Check if user is already logged in
  const isLoggedIn = typeof window !== 'undefined' && window.localStorage.getItem('auth') === 'true';

  if (isLoggedIn) {
    return (
      <div className="page">
        <header className="topbar">
          <div className="brand">
            <span className="brand-accent">FAMA</span>
            <span className="brand-sub">– secure chat</span>
          </div>
          <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="dot" />
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </header>
        <main className="hero">
          <h1 className="title">Welcome back!</h1>
          <p className="subtitle">You are already logged in. Go to chat to start messaging.</p>
          <div className="cta-row">
            <button className="btn primary" onClick={() => navigate('/chat')}>
              Go to Chat
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="brand-accent">FAMA</span>
          <span className="brand-sub">– secure chat</span>
        </div>

      
        <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="dot" />
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>
      <main className="hero">
        <h1 className="title">FAMA</h1>
        <p className="subtitle">
          Experience truly secure communication with end-to-end encryption. FAMA
          provides a private, encrypted chat platform where your conversations remain
          confidential and protected.
        </p>

        <div className="cta-row">
          <button className="btn primary" onClick={() => navigate('/login')}>
            Login
          </button>
          <button className="btn ghost" onClick={() => navigate('/register')}>
            Register
          </button>
        </div>

        <section className="features">
          <article className="card">
            <h3>
              End-to-End
              <br />
              Encrypted
            </h3>
            <p>Your messages are secured with military-grade encryption</p>
          </article>

          <article className="card">
            <h3>Private &amp; Secure</h3>
            <p>
              No data collection, no tracking, full privacy, and complete control
            </p>
          </article>

          <article className="card">
            <h3>
              Real-time
              <br />
              Messaging
            </h3>
            <p>Instant message delivery with connection status updates</p>
          </article>
        </section>
      </main>
    </div>
  );
}
