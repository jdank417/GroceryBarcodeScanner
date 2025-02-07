// src/AdminLogin.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const AdminLogin = () => {
  const [password, setPassword] = useState('');
  const [feedback, setFeedback] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        navigate('/dashboard');
      } else {
        setFeedback(data.error || 'Login failed.');
      }
    } catch (error) {
      console.error(error);
      setFeedback('An error occurred during login.');
    }
  };

  return (
    <main style={{ margin: '40px auto', maxWidth: '400px' }}>
      <h2 style={{ textAlign: 'center' }}>Admin Login</h2>
      {feedback && <div style={{ color: 'red', marginBottom: '1rem', textAlign: 'center' }}>{feedback}</div>}
      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            style={{ width: '100%', padding: '0.5rem' }}
            required
          />
        </div>
        <button type="submit" style={{ width: '100%', padding: '0.5rem' }}>Login</button>
      </form>
    </main>
  );
};

export default AdminLogin;
