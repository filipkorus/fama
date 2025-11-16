import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import { socket } from '../services/socket';
import '../styles.css';

export const Login = () => {
  const [usernameInput, setUsernameInput] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { isConnected, register } = useWebSocket();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const u = usernameInput.trim();
    const p = password.trim();

    if (!u || !p) {
      setError('Wpisz login i hasło.');
      return;
    }

    try {
      setLoading(true);

      // POST /api/auth/login  (baseURL = `${API_URL}/api`)
      const response = await api.post('/auth/login', {
        username: u,
        password: p,
      });

      console.log('Login response:', response.data);

      // Store auth flag, username and access token (if returned)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('auth', 'true');
        window.localStorage.setItem('username', u);

        const token = response.data && (response.data as any).access_token;
        if (token) {
          window.localStorage.setItem('authToken', token);

          // Attach token to API client for subsequent requests
          try {
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          } catch (err) {
            console.warn('Could not set default Authorization header on api client', err);
          }

          // Make sure Socket.IO sends token during handshake: set auth (with Bearer) and reconnect
          try {
            const bearer = `Bearer ${token}`;
            ;(socket as any).auth = { token: bearer };
            if (socket.connected) {
              socket.disconnect();
            }
            socket.connect();

            // wait for socket to connect (with a short timeout)
            await new Promise<void>((resolve, reject) => {
              const onConnect = () => {
                socket.off('connect', onConnect);
                clearTimeout(timer);
                resolve();
              };
              const timer = setTimeout(() => {
                socket.off('connect', onConnect);
                reject(new Error('Timed out waiting for socket connect'));
              }, 5000);
              socket.on('connect', onConnect);
            });
          } catch (err) {
            console.warn('Socket connect with token failed', err);
          }
        }
      }

      // Register on WebSocket layer (the hook will emit register)
      register(u);

      navigate('/chat');
    } catch (err: any) { // to any do zmiany -> zła praktyka
      console.error('Login error:', err);
      const message =
        err?.response?.data?.message ||
        err?.response?.data?.error ||
        'Logowanie nie powiodło się. Sprawdź dane i spróbuj ponownie.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <header className="topbar">
        <div className="brand">
          <span className="brand-accent">FAMA</span>
          <span className="brand-sub">– secure chat</span>
        </div>
        <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </header>

      <div className="auth-card-login">
        <h2 className="auth-card-title">Login</h2>

        <div className="input-section">
          <label htmlFor="username">Username:</label>
          <input
            id="username"
            name="username"
            type="text"
            placeholder="your_username"
            value={usernameInput}
            onChange={(e) => setUsernameInput(e.target.value)}
          />

          <label htmlFor="password">Password:</label>
          <input
            id="password"
            name="password"
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <p className="form-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Logging in…' : 'Login'}
          </button>
        </div>

        <div className="switch-form">
          <button type="button" onClick={() => navigate('/register')}>
            Don&apos;t have an account? Register here.
          </button>
        </div>
      </div>
    </form>
  );
};
