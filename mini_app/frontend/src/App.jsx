import React from 'react';
import { useApp } from './context';

// Specialist pages
import { AllOrdersPage } from './pages/SpecialistOrders';
import { MyOrdersSpecialistPage } from './pages/SpecialistMyOrders';
import { SpecialistProfilePage } from './pages/SpecialistProfile';

// Employer pages
import { EmployerOrdersPage } from './pages/EmployerOrders';
import { SpecialistsPage } from './pages/EmployerSpecialists';
import { EmployerProfilePage } from './pages/EmployerProfile';

const specialistTabs = [
  { key: 'orders', label: 'Все заказы', icon: '📋', page: AllOrdersPage },
  { key: 'my', label: 'Мои заказы', icon: '🏆', page: MyOrdersSpecialistPage },
  { key: 'profile', label: 'Профиль', icon: '👤', page: SpecialistProfilePage },
];

const employerTabs = [
  { key: 'orders', label: 'Мои заказы', icon: '📋', page: EmployerOrdersPage },
  { key: 'specs', label: 'Исполнители', icon: '🧠', page: SpecialistsPage },
  { key: 'profile', label: 'Профиль', icon: '👤', page: EmployerProfilePage },
];

export default function App() {
  const { user } = useApp();
  const [activeTab, setActiveTab] = React.useState('orders');

  if (!user) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--tg-theme-bg-color, #fff)',
        color: 'var(--tg-theme-text-color, #000)', padding: 24, textAlign: 'center',
      }}>
        <div>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🤖</div>
          <h2 style={{ margin: '0 0 8px' }}>AI Talent Hub</h2>
          <p style={{ opacity: 0.6, fontSize: 14 }}>
            Зарегистрируйтесь в боте, чтобы использовать Mini App
          </p>
        </div>
      </div>
    );
  }

  const tabs = user.role === 'employer' ? employerTabs : specialistTabs;
  const activeTabData = tabs.find(t => t.key === activeTab) || tabs[0];
  const PageComponent = activeTabData.page;

  const tg = window.Telegram?.WebApp;
  const bgColor = tg?.themeParams?.bg_color
    ? `#${tg.themeParams.bg_color.toString(16).padStart(6, '0')}`
    : '#ffffff';
  const textColor = tg?.themeParams?.text_color
    ? `#${tg.themeParams.text_color.toString(16).padStart(6, '0')}`
    : '#000000';
  const btnColor = tg?.themeParams?.button_color
    ? `#${tg.themeParams.button_color.toString(16).padStart(6, '0')}`
    : '#3390ec';
  const secBgColor = tg?.themeParams?.secondary_bg_color
    ? `#${tg.themeParams.secondary_bg_color.toString(16).padStart(6, '0')}`
    : '#f4f4f5';

  return (
    <div style={{
      minHeight: '100vh',
      background: bgColor,
      color: textColor,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      paddingBottom: 70,
      '--tg-theme-bg-color': bgColor,
      '--tg-theme-text-color': textColor,
      '--tg-theme-button-color': btnColor,
      '--tg-theme-secondary-bg-color': secBgColor,
      '--tg-theme-hint-color': '#999999',
    }}>
      {/* Заголовок */}
      <div style={{
        padding: '12px 16px', borderBottom: `1px solid ${secBgColor}`,
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontSize: 20 }}>🤖</span>
        <span style={{ fontWeight: 700, fontSize: 16 }}>AI Talent Hub</span>
        <span style={{
          marginLeft: 'auto', fontSize: 12, padding: '2px 8px',
          borderRadius: 8, background: btnColor + '22', color: btnColor,
        }}>
          {user.role === 'employer' ? '🏢 Предприниматель' : '🧠 Специалист'}
        </span>
      </div>

      {/* Контент */}
      <PageComponent />

      {/* Нижняя навигация */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        background: bgColor,
        borderTop: `1px solid ${secBgColor}`,
        display: 'flex', padding: '8px 0',
        paddingBottom: 'max(8px, env(safe-area-inset-bottom))',
      }}>
        {tabs.map(tab => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                flex: 1, background: 'none', border: 'none',
                cursor: 'pointer', padding: '6px 0',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
                color: isActive ? btnColor : textColor,
                opacity: isActive ? 1 : 0.5,
              }}
            >
              <span style={{ fontSize: 22 }}>{tab.icon}</span>
              <span style={{ fontSize: 11, fontWeight: isActive ? 600 : 400 }}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
