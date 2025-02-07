// src/NavBar.js
import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const NavBar = () => {
  const [theme, setTheme] = useState('light');
  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <header style={{ padding: '1rem', backgroundColor: theme === 'light' ? '#000' : '#222', color: '#FFD700', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <Link to="/" style={{ color: '#FFD700', textDecoration: 'none', fontWeight: 'bold' }}>Wentworth</Link>
      </div>
      <nav>
        <Link to="/" style={{ marginRight: '1rem', color: '#FFD700', textDecoration: 'none' }}>Home</Link>
        <Link to="/login" style={{ marginRight: '1rem', color: '#FFD700', textDecoration: 'none' }}>Admin Login</Link>
        <Link to="/dashboard" style={{ color: '#FFD700', textDecoration: 'none' }}>Dashboard</Link>
      </nav>
      <div>
        <button onClick={toggleTheme} style={{ background: 'none', border: 'none', color: '#FFD700', cursor: 'pointer' }}>
          {theme === 'light' ? "Switch to Dark Mode" : "Switch to Light Mode"}
        </button>
      </div>
    </header>
  );
};

export default NavBar;
