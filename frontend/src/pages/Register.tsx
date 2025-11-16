import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import { socket } from '../services/socket';
import { generateMLKEMKeypair, storeKeysLocally, getStoredKeyInfo } from '../services/crypto';
import '../styles.css';


export const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { isConnected, register } = useWebSocket();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const u = username.trim();
    const p = password.trim();
    const cp = confirmPassword.trim();

    if (!u || !p || !cp) {
      setError('Wszystkie pola są wymagane.');
      return;
    }

    if (p !== cp) {
      setError('Hasła muszą być takie same.');
      return;
    }

    try {
      setLoading(true);

      // Generate ML-KEM (Kyber768) keypair on client side
      console.log('Starting key generation...');
      let publicKey: string;
      let privateKey: string;
      
      try {
        const result = await generateMLKEMKeypair();
        publicKey = result.publicKey;
        privateKey = result.privateKey;
        console.log('Key generation result:', { publicKeyExists: !!publicKey, privateKeyExists: !!privateKey });
      } catch (keyGenError) {
        console.error('Key generation failed:', keyGenError);
        throw keyGenError;
      }
      
      if (!publicKey || !privateKey) {
        throw new Error('Key generation returned undefined values');
      }
      
      console.log('Generated keys - Public:', publicKey ? `${publicKey.substring(0, 50)}...` : 'undefined', 'Private:', privateKey ? `${privateKey.substring(0, 50)}...` : 'undefined');

      // Store keys in localStorage for persistent memory
      try {
        storeKeysLocally(publicKey, privateKey);
      } catch (storageError) {
        console.error('Storage failed:', storageError);
        throw storageError;
      }
      
      // Log key info for debugging
      const keyInfo = getStoredKeyInfo();
      console.log('Stored key info:', keyInfo);

      // Register user with public key
      console.log('Sending registration request with public_key:', publicKey ? `${publicKey.substring(0, 50)}...` : 'MISSING');
      const response = await api.post('/auth/register', { 
        username: u, 
        password: p, 
        public_key: publicKey 
      });

      console.log('Registration successful');

      // Store auth data immediately after registration
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

          // Ensure Socket.IO uses token during handshake
          try {
            const bearer = `Bearer ${token}`;
            ;(socket as any).auth = { token: bearer };
            if (socket.connected) {
              socket.disconnect();
            }
            socket.connect();

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

      // Register in WebSocket layer
      register(u);

      navigate('/chat');
    } catch (err: any) {
      console.error('Register error:', err);
      const message =
        err?.response?.data?.message ||
        err?.response?.data?.error ||
        'Rejestracja nie powiodła się. Spróbuj ponownie.';
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

      <div className="auth-card-register">
        <h2 className="auth-card-title">Register</h2>

        <div className="input-section">
          <label htmlFor="username">Username:</label>
          <input
            id="username"
            name="username"
            type="text"
            placeholder="your_username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
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

          <label htmlFor="confirmPassword">Confirm password:</label>
          <input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            placeholder="Repeat password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />

          {error && <p className="form-error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Registering…' : 'Register'}
          </button>
        </div>

        <div className="switch-form">
          <button type="button" onClick={() => navigate('/login')}>
            Already have an account? Login here.
          </button>
        </div>
      </div>
    </form>
  );
};
