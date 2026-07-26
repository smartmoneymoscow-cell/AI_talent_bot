import React, { useState, useEffect } from 'react';
import { useApp } from '../context';
import { api } from '../api';
import { Avatar, Stars, Loader } from '../components';

export function EmployerProfilePage() {
  const { user, refreshUser } = useApp();
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.getMyStats().then(setStats).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateMe({ bio });
      await refreshUser();
      setEditing(false);
    } catch (e) { alert(e.message); }
    finally { setSaving(false); }
  }

  async function handleSwitchRole() {
    if (!confirm('Сменить роль на «Специалист»?')) return;
    setSwitching(true);
    try {
      await api.switchRole();
      await refreshUser();
    } catch (e) { alert(e.message); }
    finally { setSwitching(false); }
  }

  if (!user) return <Loader />;

  return (
    <div style={{ padding: 16 }}>
      {/* Шапка */}
      <div style={{
        textAlign: 'center', padding: '24px 16px', marginBottom: 16,
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)', borderRadius: 16,
      }}>
        <Avatar telegramId={user.telegram_id} name={user.full_name} size={80} />
        <h2 style={{ margin: '12px 0 4px', fontSize: 20 }}>{user.full_name}</h2>
        {user.username && <div style={{ fontSize: 14, opacity: 0.5 }}>@{user.username}</div>}
      </div>

      {/* Статистика */}
      {stats && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16,
        }}>
          {[
            { label: 'Всего заказов', value: Object.values(stats.orders_by_status || {}).reduce((a, b) => a + b, 0), icon: '📋' },
            { label: 'Открытых', value: stats.orders_by_status?.open || 0, icon: '🟢' },
            { label: 'В работе', value: stats.orders_by_status?.in_progress || 0, icon: '🟡' },
            { label: 'Потрачено', value: `${((stats.total_spent || 0) / 100).toLocaleString('ru-RU')} ₽`, icon: '💰' },
          ].map(s => (
            <div key={s.label} style={{
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              borderRadius: 10, padding: 12, textAlign: 'center',
            }}>
              <div style={{ fontSize: 20 }}>{s.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 16, margin: '4px 0' }}>{s.value}</div>
              <div style={{ fontSize: 12, opacity: 0.5 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Описание */}
      {editing ? (
        <div>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            О себе и компании
          </label>
          <textarea
            value={bio} onChange={e => setBio(e.target.value)} rows={4}
            style={{
              width: '100%', padding: 10, borderRadius: 10,
              border: '1px solid #99944',
              background: 'var(--tg-theme-bg-color, #fff)',
              color: 'var(--tg-theme-text-color, #000)', fontSize: 14,
              resize: 'vertical', boxSizing: 'border-box',
            }}
            placeholder="Расскажите о вашем бизнесе..."
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button onClick={handleSave} disabled={saving} style={primaryBtn}>
              {saving ? '⏳...' : '✅ Сохранить'}
            </button>
            <button onClick={() => setEditing(false)} style={secondaryBtn}>Отмена</button>
          </div>
        </div>
      ) : (
        <div>
          <div style={{
            background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
            borderRadius: 12, padding: 16, marginBottom: 12,
          }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🏢 О компании</h3>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>
              {user.bio || 'Не заполнено'}
            </p>
          </div>
          <button onClick={() => { setBio(user.bio || ''); setEditing(true); }}
            style={{ ...primaryBtn, width: '100%', marginBottom: 12 }}>
            ✏️ Редактировать
          </button>

          <button
            onClick={handleSwitchRole}
            disabled={switching}
            style={{
              width: '100%', padding: '12px 0', borderRadius: 10,
              border: '1px solid var(--tg-theme-hint-color, #999)44',
              background: 'transparent',
              color: 'var(--tg-theme-hint-color, #999)',
              cursor: 'pointer', fontSize: 14,
              opacity: switching ? 0.5 : 1,
            }}
          >
            {switching ? '⏳...' : '🔄 Сменить роль на специалиста'}
          </button>
        </div>
      )}
    </div>
  );
}

const primaryBtn = {
  padding: '12px 24px', borderRadius: 10, border: 'none',
  background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
  cursor: 'pointer', fontSize: 14, fontWeight: 600,
};
const secondaryBtn = {
  ...primaryBtn, background: 'var(--tg-theme-hint-color, #999)33',
  color: 'var(--tg-theme-text-color, #000)',
};
