import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, getTelegramUser } from './api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tgUser, setTgUser] = useState(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
    }
    // Get Telegram user data for quick registration
    const tUser = getTelegramUser();
    setTgUser(tUser);
    loadUser();
  }, []);

  async function loadUser() {
    try {
      const me = await api.getMe();
      setUser(me);
    } catch (e) {
      console.error('Failed to load user:', e);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  function refreshUser() {
    return api.getMe().then(setUser);
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--tg-theme-bg-color, #fff)',
        color: 'var(--tg-theme-text-color, #000)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>🤖</div>
          <div>Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <AppContext.Provider value={{ user, setUser, refreshUser, loadUser, tgUser }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
