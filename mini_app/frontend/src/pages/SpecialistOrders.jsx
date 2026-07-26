import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { OrderCard, EmptyState, Loader } from '../components';

export function AllOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [minBudget, setMinBudget] = useState('');
  const [maxBudget, setMaxBudget] = useState('');
  const [sort, setSort] = useState('newest');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => { loadOrders(); }, [sort]);

  async function loadOrders(params = {}) {
    setLoading(true);
    try {
      const data = await api.getOrders({
        search: search || undefined,
        min_budget: minBudget || undefined,
        max_budget: maxBudget || undefined,
        sort,
        ...params,
      });
      setOrders(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e) {
    e.preventDefault();
    loadOrders();
  }

  if (selectedOrder) {
    return <OrderDetail order={selectedOrder} onBack={() => { setSelectedOrder(null); loadOrders(); }} />;
  }

  return (
    <div style={{ padding: 16 }}>
      {/* Поиск */}
      <form onSubmit={handleSearch} style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder="🔍 Поиск заказов..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 10, border: '1px solid var(--tg-theme-hint-color, #999)44',
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              color: 'var(--tg-theme-text-color, #000)', fontSize: 14,
            }}
          />
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            style={{
              padding: '10px 14px', borderRadius: 10, border: 'none',
              background: showFilters ? 'var(--tg-theme-button-color, #3390ec)' : 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              color: showFilters ? '#fff' : 'var(--tg-theme-text-color, #000)',
              cursor: 'pointer', fontSize: 16,
            }}
          >
            ⚙️
          </button>
        </div>

        {/* Фильтры */}
        {showFilters && (
          <div style={{
            marginTop: 8, padding: 12, borderRadius: 10,
            background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input
                type="number" placeholder="Бюджет от" value={minBudget}
                onChange={e => setMinBudget(e.target.value)}
                style={{
                  flex: 1, padding: '8px 10px', borderRadius: 8, border: '1px solid #99944',
                  background: 'var(--tg-theme-bg-color, #fff)',
                  color: 'var(--tg-theme-text-color, #000)', fontSize: 13,
                }}
              />
              <input
                type="number" placeholder="Бюджет до" value={maxBudget}
                onChange={e => setMaxBudget(e.target.value)}
                style={{
                  flex: 1, padding: '8px 10px', borderRadius: 8, border: '1px solid #99944',
                  background: 'var(--tg-theme-bg-color, #fff)',
                  color: 'var(--tg-theme-text-color, #000)', fontSize: 13,
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {['newest', 'budget'].map(s => (
                <button
                  key={s}
                  onClick={() => setSort(s)}
                  style={{
                    flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
                    background: sort === s ? 'var(--tg-theme-button-color, #3390ec)' : 'var(--tg-theme-bg-color, #fff)',
                    color: sort === s ? '#fff' : 'var(--tg-theme-text-color, #000)',
                    cursor: 'pointer', fontSize: 13,
                  }}
                >
                  {s === 'newest' ? '📅 Новые' : '💰 По цене'}
                </button>
              ))}
            </div>
            <button
              type="submit"
              style={{
                width: '100%', marginTop: 8, padding: '8px 0', borderRadius: 8, border: 'none',
                background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
                cursor: 'pointer', fontSize: 14, fontWeight: 600,
              }}
            >
              Применить
            </button>
          </div>
        )}
      </form>

      {loading ? <Loader /> : orders.length === 0 ? (
        <EmptyState icon="📭" text="Заказов не найдено" />
      ) : (
        orders.map(o => (
          <OrderCard key={o.id} order={o} onClick={() => setSelectedOrder(o)} />
        ))
      )}
    </div>
  );
}


function OrderDetail({ order, onBack }) {
  const [applications, setApplications] = useState([]);
  const [showApplyForm, setShowApplyForm] = useState(false);
  const [applyMsg, setApplyMsg] = useState('');
  const [applyPrice, setApplyPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [myApp, setMyApp] = useState(null);

  useEffect(() => {
    loadApplications();
  }, []);

  async function loadApplications() {
    try {
      const apps = await api.getApplications(order.id);
      setApplications(apps);
    } catch (e) {}
  }

  async function handleApply(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createApplication({
        order_id: order.id,
        message: applyMsg,
        proposed_price: applyPrice ? parseInt(applyPrice) : 0,
      });
      setShowApplyForm(false);
      setApplyMsg('');
      setApplyPrice('');
      await loadApplications();
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      {/* Кнопка назад */}
      <button
        onClick={onBack}
        style={{
          background: 'none', border: 'none', color: 'var(--tg-theme-button-color, #3390ec)',
          cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 12,
        }}
      >
        ← Назад к заказам
      </button>

      {/* Карточка заказа */}
      <div style={{
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 12, padding: 16, marginBottom: 16,
      }}>
        <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>{order.title}</h2>
        <div style={{ display: 'flex', gap: 12, fontSize: 13, opacity: 0.6, marginBottom: 12 }}>
          {order.budget > 0 && <span>💰 {order.budget.toLocaleString('ru-RU')} ₽</span>}
          {order.employer_name && <span>🏢 {order.employer_name}</span>}
        </div>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>{order.description}</p>
      </div>

      {/* Кнопка отклика */}
      {order.status === 'open' && !showApplyForm && (
        <button
          onClick={() => setShowApplyForm(true)}
          style={{
            width: '100%', padding: '12px 0', borderRadius: 10, border: 'none',
            background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
            cursor: 'pointer', fontSize: 15, fontWeight: 600, marginBottom: 16,
          }}
        >
          📩 Откликнуться
        </button>
      )}

      {/* Форма отклика */}
      {showApplyForm && (
        <form onSubmit={handleApply} style={{
          background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          borderRadius: 12, padding: 16, marginBottom: 16,
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>📩 Ваш отклик</h3>
          <textarea
            placeholder="Почему вы подходите? Ваш опыт..."
            value={applyMsg}
            onChange={e => setApplyMsg(e.target.value)}
            rows={3}
            style={{
              width: '100%', padding: 10, borderRadius: 8, border: '1px solid #99944',
              background: 'var(--tg-theme-bg-color, #fff)',
              color: 'var(--tg-theme-text-color, #000)', fontSize: 14, resize: 'vertical',
              boxSizing: 'border-box',
            }}
          />
          <input
            type="number"
            placeholder="💰 Ваша цена (₽)"
            value={applyPrice}
            onChange={e => setApplyPrice(e.target.value)}
            style={{
              width: '100%', padding: '10px', borderRadius: 8, border: '1px solid #99944',
              background: 'var(--tg-theme-bg-color, #fff)',
              color: 'var(--tg-theme-text-color, #000)', fontSize: 14,
              marginTop: 8, boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button
              type="submit"
              disabled={submitting}
              style={{
                flex: 1, padding: '10px 0', borderRadius: 8, border: 'none',
                background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
                cursor: 'pointer', fontSize: 14, fontWeight: 600,
              }}
            >
              {submitting ? '⏳...' : '✅ Отправить'}
            </button>
            <button
              type="button"
              onClick={() => setShowApplyForm(false)}
              style={{
                padding: '10px 16px', borderRadius: 8, border: 'none',
                background: 'var(--tg-theme-hint-color, #999)33',
                color: 'var(--tg-theme-text-color, #000)',
                cursor: 'pointer', fontSize: 14,
              }}
            >
              Отмена
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
