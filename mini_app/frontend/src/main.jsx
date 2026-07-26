import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { AppProvider } from './context';

// Global error handler
window.addEventListener('error', (e) => {
  console.error('Global error:', e);
  const root = document.getElementById('root');
  if (root && !root.querySelector('[data-app]')) {
    root.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;padding:24px;">
        <div>
          <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
          <h2>Ошибка загрузки</h2>
          <p style="opacity:0.6;margin-top:8px;font-size:14px;">${e.message || 'Перезапустите приложение'}</p>
          <button onclick="window.location.reload()" style="margin-top:16px;padding:12px 24px;border-radius:12px;border:none;background:#3390ec;color:#fff;cursor:pointer;font-size:15px;">
            🔄 Перезагрузить
          </button>
        </div>
      </div>`;
  }
});

window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled rejection:', e);
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AppProvider>
      <App />
    </AppProvider>
  </React.StrictMode>
);
