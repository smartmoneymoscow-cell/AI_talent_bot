import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, getTelegramUser } from './api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tgUser, setTgUser] = useState(null);

  useEffect(() => {
    try {
      const tg = window.Telegram?.WebApp;
      if (tg) { tg.ready(); tg.expand(); }
    } catch (e) { console.warn('TG init:', e); }

    try { setTgUser(getTelegramUser()); } catch (e) {}

    const timeout = setTimeout(() => setLoading(false), 5000);
    loadUser().finally(() => clearTimeout(timeout));
    return () => clearTimeout(timeout);
  }, []);

  async function loadUser() {
    try {
      const me = await api.getMe();
      // If user has no role, they need registration
      if (me && !me.role && me.is_new) {
        setUser(null); // Show register page
      } else {
        setUser(me);
      }
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  function refreshUser() {
    return api.getMe().then(u => {
      if (u && !u.role && u.is_new) setUser(null);
      else setUser(u);
    }).catch(() => setUser(null));
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
