import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { EmptyState, Loader, Badge, Stars } from '../components';

export function MyOrdersSpecialistPage() {
  const [tab, setTab] = useState('applications'); // 'applications' | 'orders'
  const [applications, setApplications] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (tab === 'applications') loadApplications();
    else loadOrders();
  }, [tab]);

  async function loadApplications() {
    setLoading(true);
    try {
      const data = await api.getMyApplications();
      setApplications(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function loadOrders() {
    setLoading(true);
    try {
      const data = await api.getOrders({ status: 'in_progress' });
      const completed = await api.getOrders({ status: 'completed' });
      setOrders([...data, ...completed]);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  const statusMap = {
    pending: { label: '⏳ Ожидает', color: '#ff9800' },
    accepted: { label: '✅ Принят', color: '#4caf50' },
    rejected: { label: '❌ Отклонён', color: '#f44336' },
    withdrawn: { label: '↩️ Отозван', color: '#999' },
  };

  return (
    <div style={{ padding: 16 }}>
      {/* Табы */}
      <div style={{
        display: 'flex', gap: 8, marginBottom: 16,
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 10, padding: 4,
      }}>
        {[
          { key: 'applications', label: '📋 Мои отклики' },
          { key: 'orders', label: '🏆 Заказы' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1, padding: '8px 0', borderRadius: 8, border: 'none',
              background: tab === t.key ? 'var(--tg-theme-button-color, #3390ec)' : 'transparent',
              color: tab === t.key ? '#fff' : 'var(--tg-theme-text-color, #000)',
              cursor: 'pointer', fontSize: 13, fontWeight: tab === t.key ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <Loader /> : tab === 'applications' ? (
        applications.length === 0 ? (
          <EmptyState icon="📋" text="У вас пока нет откликов" />
        ) : (
          applications.map(app => {
            const status = statusMap[app.status] || { label: app.status, color: '#999' };
            return (
              <div key={app.id} style={{
                background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
                borderRadius: 12, padding: 16, marginBottom: 12,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: 15 }}>{app.order_title}</h3>
                    <div style={{ fontSize: 13, opacity: 0.6, marginTop: 4 }}>
                      🏢 {app.employer_name}
                    </div>
                  </div>
                  <Badge color={status.color}>{status.label}</Badge>
                </div>
                {app.order_budget > 0 && (
                  <div style={{ fontSize: 13, opacity: 0.6 }}>
                    💰 Бюджет: {app.order_budget.toLocaleString('ru-RU')} ₽
                  </div>
                )}
                {app.proposed_price > 0 && (
                  <div style={{ fontSize: 13, color: 'var(--tg-theme-button-color, #3390ec)', fontWeight: 600 }}>
                    💰 Ваша цена: {app.proposed_price.toLocaleString('ru-RU')} ₽
                  </div>
                )}
                {app.message && (
                  <p style={{ margin: '8px 0 0', fontSize: 14, opacity: 0.8 }}>
                    💬 {app.message}
                  </p>
                )}
              </div>
            );
          })
        )
      ) : (
        orders.length === 0 ? (
          <EmptyState icon="🏆" text="Нет заказов в работе" />
        ) : (
          orders.map(o => (
            <div key={o.id} style={{
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              borderRadius: 12, padding: 16, marginBottom: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <h3 style={{ margin: 0, fontSize: 15 }}>{o.title}</h3>
                <Badge color={o.status === 'completed' ? '#4caf50' : '#ff9800'}>
                  {o.status === 'completed' ? '✅ Завершён' : '🟡 В работе'}
                </Badge>
              </div>
              <div style={{ fontSize: 13, opacity: 0.6 }}>
                🏢 {o.employer_name}
                {o.budget > 0 && ` · 💰 ${o.budget.toLocaleString('ru-RU')} ₽`}
              </div>
            </div>
          ))
        )
      )}
    </div>
  );
}
