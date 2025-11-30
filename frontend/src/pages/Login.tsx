import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { initializeAuth, storeAuthData } from '../services/auth';
import '../styles.css';

export const Login = () => {
  const [usernameInput, setUsernameInput] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

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

      const token = response.data && (response.data as any).access_token;
      if (token) {
        storeAuthData(token, u);
        await initializeAuth(token);
      }

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
