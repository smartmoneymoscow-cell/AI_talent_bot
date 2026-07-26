import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { OrderCard, Avatar, Stars, EmptyState, Loader, Badge } from '../components';

export function EmployerOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => { loadOrders(); }, []);

  async function loadOrders() {
    setLoading(true);
    try {
      const data = await api.getOrders();
      setOrders(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  if (selectedOrder) {
    return <EmployerOrderDetail order={selectedOrder} onBack={() => { setSelectedOrder(null); loadOrders(); }} />;
  }

  if (showCreate) {
    return <CreateOrderForm onBack={() => { setShowCreate(false); loadOrders(); }} />;
  }

  return (
    <div style={{ padding: 16 }}>
      {/* Кнопка создания */}
      <button
        onClick={() => setShowCreate(true)}
        style={{
          width: '100%', padding: '14px 0', borderRadius: 12, border: 'none',
          background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
          cursor: 'pointer', fontSize: 15, fontWeight: 600, marginBottom: 16,
        }}
      >
        ＋ Создать заказ
      </button>

      {loading ? <Loader /> : orders.length === 0 ? (
        <EmptyState icon="📝" text="У вас пока нет заказов" />
      ) : (
        orders.map(o => (
          <OrderCard key={o.id} order={o} onClick={() => setSelectedOrder(o)} />
        ))
      )}
    </div>
  );
}


function CreateOrderForm({ onBack }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [budget, setBudget] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      alert('Заполните название и описание');
      return;
    }
    setSubmitting(true);
    try {
      await api.createOrder({
        title: title.trim(),
        description: description.trim(),
        budget: budget ? parseInt(budget) : 0,
      });
      onBack();
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <button onClick={onBack} style={backBtn}>← Назад</button>
      <h2 style={{ margin: '0 0 16px', fontSize: 18 }}>📝 Новый заказ</h2>

      <form onSubmit={handleSubmit}>
        <label style={labelStyle}>Название</label>
        <input
          value={title} onChange={e => setTitle(e.target.value)}
          placeholder="Что нужно сделать?" style={inputStyle}
          maxLength={200}
        />

        <label style={labelStyle}>Описание</label>
        <textarea
          value={description} onChange={e => setDescription(e.target.value)}
          placeholder="Подробное описание задачи, требования, ожидаемый результат..."
          rows={5} style={textareaStyle}
        />

        <label style={labelStyle}>Бюджет (₽)</label>
        <input
          type="number" value={budget} onChange={e => setBudget(e.target.value)}
          placeholder="50000" style={inputStyle}
        />

        <button
          type="submit" disabled={submitting}
          style={{
            ...primaryBtn, width: '100%', marginTop: 16,
            opacity: submitting ? 0.6 : 1,
          }}
        >
          {submitting ? '⏳ Создаю...' : '✅ Создать заказ'}
        </button>
      </form>
    </div>
  );
}


function EmployerOrderDetail({ order, onBack }) {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadApps(); }, []);

  async function loadApps() {
    setLoading(true);
    try {
      const data = await api.getApplications(order.id);
      setApplications(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  async function handleAccept(appId) {
    if (!confirm('Выбрать этого исполнителем?')) return;
    try {
      await api.acceptApplication(appId);
      await loadApps();
    } catch (e) { alert(e.message); }
  }

  async function handleReject(appId) {
    try {
      await api.rejectApplication(appId);
      await loadApps();
    } catch (e) { alert(e.message); }
  }

  async function handleComplete() {
    if (!confirm('Отправить на проверку?')) return;
    try {
      await api.updateOrderStatus(order.id, 'review');
      onBack();
    } catch (e) { alert(e.message); }
  }

  const statusMap = {
    open: { label: '🟢 Открыт', color: '#4caf50' },
    in_progress: { label: '🟡 В работе', color: '#ff9800' },
    review: { label: '🔵 На проверке', color: '#2196f3' },
    completed: { label: '✅ Завершён', color: '#4caf50' },
    cancelled: { label: '❌ Отменён', color: '#f44336' },
  };
  const status = statusMap[order.status] || { label: order.status, color: '#999' };

  return (
    <div style={{ padding: 16 }}>
      <button onClick={onBack} style={backBtn}>← Назад к заказам</button>

      {/* Карточка заказа */}
      <div style={{
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 12, padding: 16, marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>{order.title}</h2>
          <Badge color={status.color}>{status.label}</Badge>
        </div>
        {order.budget > 0 && (
          <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--tg-theme-button-color, #3390ec)' }}>
            💰 {order.budget.toLocaleString('ru-RU')} ₽
          </div>
        )}
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>{order.description}</p>
      </div>

      {/* Кнопки управления */}
      {order.status === 'in_progress' && (
        <button onClick={handleComplete} style={{ ...primaryBtn, width: '100%', marginBottom: 16 }}>
          ✅ Завершить (на проверку)
        </button>
      )}

      {/* Отклики */}
      <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>
        📩 Отклики ({applications.length})
      </h3>

      {loading ? <Loader /> : applications.length === 0 ? (
        <EmptyState icon="📭" text="Пока нет откликов" />
      ) : (
        applications.map(app => (
          <div key={app.id} style={{
            background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
            borderRadius: 12, padding: 16, marginBottom: 12,
            border: app.status === 'accepted' ? '2px solid #4caf50' :
                    app.status === 'rejected' ? '2px solid #f44336' : 'none',
          }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
              <Avatar telegramId={app.specialist_tg_id} name={app.specialist_name} size={40} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{app.specialist_name}</div>
                <Stars rating={app.specialist_rating} count={0} />
              </div>
              {app.proposed_price > 0 && (
                <div style={{ fontWeight: 600, color: 'var(--tg-theme-button-color, #3390ec)' }}>
                  {app.proposed_price.toLocaleString('ru-RU')} ₽
                </div>
              )}
            </div>

            {app.specialist_skills && (
              <div style={{ fontSize: 13, opacity: 0.6, marginBottom: 4 }}>
                🛠 {app.specialist_skills}
              </div>
            )}
            <div style={{ fontSize: 13, opacity: 0.5, marginBottom: 8 }}>
              ✅ {app.specialist_jobs} заказов
            </div>

            {app.message && (
              <p style={{ margin: '0 0 8px', fontSize: 14, lineHeight: 1.4 }}>
                💬 {app.message}
              </p>
            )}

            {app.status === 'pending' && order.status === 'open' && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button
                  onClick={() => handleAccept(app.id)}
                  style={{
                    flex: 1, padding: '8px 0', borderRadius: 8, border: 'none',
                    background: '#4caf50', color: '#fff', cursor: 'pointer',
                    fontSize: 13, fontWeight: 600,
                  }}
                >
                  ✅ Выбрать исполнителем
                </button>
                <button
                  onClick={() => handleReject(app.id)}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: 'none',
                    background: '#f4433622', color: '#f44336', cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  ❌
                </button>
              </div>
            )}

            {app.status === 'accepted' && (
              <Badge color="#4caf50">✅ Исполнитель</Badge>
            )}
            {app.status === 'rejected' && (
              <Badge color="#f44336">❌ Отклонён</Badge>
            )}
          </div>
        ))
      )}
    </div>
  );
}

const labelStyle = {
  display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, marginTop: 12,
};
const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #99944',
  background: 'var(--tg-theme-bg-color, #fff)',
  color: 'var(--tg-theme-text-color, #000)', fontSize: 14, boxSizing: 'border-box',
};
const textareaStyle = { ...inputStyle, resize: 'vertical', minHeight: 100 };
const primaryBtn = {
  padding: '12px 24px', borderRadius: 10, border: 'none',
  background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
  cursor: 'pointer', fontSize: 14, fontWeight: 600,
};
const backBtn = {
  background: 'none', border: 'none', color: 'var(--tg-theme-button-color, #3390ec)',
  cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 12,
};
