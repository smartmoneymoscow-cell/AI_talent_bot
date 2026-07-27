import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api, getTelegramUser } from './api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tgUser, setTgUser] = useState(null);
  const initDone = useRef(false);

  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;

    function initTG() {
      try {
        const tg = window.Telegram?.WebApp;
        if (tg && typeof tg.ready === 'function') {
          tg.ready();
          tg.expand();
        }
      } catch (e) {
        console.warn('TG init error:', e);
      }
      try {
        const u = getTelegramUser();
        if (u) setTgUser(u);
      } catch (e) {
        console.warn('TG user parse error:', e);
      }
    }

    // SDK may load async — wait for it
    if (window.Telegram?.WebApp) {
      initTG();
    } else {
      const checkInterval = setInterval(() => {
        if (window.Telegram?.WebApp) {
          clearInterval(checkInterval);
          initTG();
        }
      }, 200);
      // Stop checking after 8s, proceed without SDK
      setTimeout(() => {
        clearInterval(checkInterval);
        if (!window.Telegram?.WebApp) {
          console.warn('Telegram SDK not loaded, continuing without it');
        }
      }, 8000);
    }

    // Load user with a max 6s timeout for loading state
    const loadingTimeout = setTimeout(() => setLoading(false), 6000);
    loadUser().finally(() => {
      clearTimeout(loadingTimeout);
      setLoading(false);
    });

    return () => clearTimeout(loadingTimeout);
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
