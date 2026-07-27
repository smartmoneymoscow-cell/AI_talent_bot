import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api, getTelegramUser } from './api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tgUser, setTgUser] = useState(null);
  const mounted = useRef(true);

  useEffect(() => {
    // Init Telegram SDK
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

    // Load user — if it fails or hangs, we stop loading after 4s
    let done = false;

    function finish() {
      if (!done && mounted.current) {
        done = true;
        setLoading(false);
      }
    }

    // Hard timeout: after 4 seconds, ALWAYS stop loading
    const hardTimeout = setTimeout(finish, 4000);

    // Check if we have initData — if not, skip API call entirely
    const hasInitData = !!(window.Telegram?.WebApp?.initData);
    if (!hasInitData) {
      console.warn('No Telegram initData — showing registration page');
      setUser(null);
      clearTimeout(hardTimeout);
      finish();
      return () => { mounted.current = false; clearTimeout(hardTimeout); };
    }

    api.getMe()
      .then(me => {
        if (!mounted.current) return;
        if (me && !me.role && me.is_new) {
          setUser(null);
        } else {
          setUser(me);
        }
      })
      .catch(e => {
        console.warn('getMe error:', e);
        // On 401 or network error — show registration, not blank screen
        if (mounted.current) setUser(null);
      })
      .finally(() => {
        clearTimeout(hardTimeout);
        finish();
      });

    return () => {
      mounted.current = false;
      clearTimeout(hardTimeout);
    };
  }, []);

  function loadUser() {
    return api.getMe()
      .then(me => {
        if (me && !me.role && me.is_new) setUser(null);
        else setUser(me);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }

  function refreshUser() {
    return api.getMe()
      .then(u => {
        if (u && !u.role && u.is_new) setUser(null);
        else setUser(u);
      })
      .catch(() => setUser(null));
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
