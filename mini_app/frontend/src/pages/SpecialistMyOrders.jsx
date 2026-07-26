import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { OrderCard, EmptyState, Loader, Badge } from '../components';

export function MyOrdersSpecialistPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('in_progress');

  useEffect(() => { loadOrders(); }, [filter]);

  async function loadOrders() {
    setLoading(true);
    try {
      const data = await api.getOrders({ status: filter });
      setOrders(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      {/* Фильтры */}
      <div style={{
        display: 'flex', gap: 8, marginBottom: 16,
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 10, padding: 4,
      }}>
        {[
          { key: 'in_progress', label: '🟡 В работе' },
          { key: 'completed', label: '✅ Завершённые' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              flex: 1, padding: '8px 0', borderRadius: 8, border: 'none',
              background: filter === f.key ? 'var(--tg-theme-button-color, #3390ec)' : 'transparent',
              color: filter === f.key ? '#fff' : 'var(--tg-theme-text-color, #000)',
              cursor: 'pointer', fontSize: 13, fontWeight: filter === f.key ? 600 : 400,
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? <Loader /> : orders.length === 0 ? (
        <EmptyState icon="📋" text={filter === 'in_progress' ? 'Нет заказов в работе' : 'Нет завершённых заказов'} />
      ) : (
        orders.map(o => <OrderCard key={o.id} order={o} />)
      )}
    </div>
  );
}
