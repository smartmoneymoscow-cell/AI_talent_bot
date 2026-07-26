import React from 'react';

export function Avatar({ telegramId, name, size = 48 }) {
  const [src, setSrc] = React.useState(null);

  React.useEffect(() => {
    if (!telegramId) return;
    fetch(`/api/avatar/${telegramId}`, {
      headers: { 'X-Telegram-Init-Data': window.Telegram?.WebApp?.initData || '' },
    })
      .then(r => r.json())
      .then(data => { if (data.url) setSrc(data.url); })
      .catch(() => {});
  }, [telegramId]);

  const initial = name ? name.charAt(0).toUpperCase() : '?';

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        style={{
          width: size, height: size, borderRadius: '50%',
          objectFit: 'cover', border: '2px solid var(--tg-theme-button-color, #3390ec)',
        }}
      />
    );
  }

  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: 'var(--tg-theme-button-color, #3390ec)',
      color: '#fff', display: 'flex', alignItems: 'center',
      justifyContent: 'center', fontSize: size * 0.4, fontWeight: 700,
    }}>
      {initial}
    </div>
  );
}

export function Stars({ rating, count }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <span style={{ fontSize: 14 }}>
      {'⭐'.repeat(full)}{half ? '✨' : ''}{'☆'.repeat(empty)}
      <span style={{ opacity: 0.6, marginLeft: 4 }}>
        ({rating?.toFixed(1) || '0'}{count ? `, ${count}` : ''})
      </span>
    </span>
  );
}

export function Badge({ children, color = 'var(--tg-theme-button-color, #3390ec)' }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: 12,
      fontSize: 12, fontWeight: 600, background: color + '22', color,
    }}>
      {children}
    </span>
  );
}

export function OrderCard({ order, onClick }) {
  const statusMap = {
    open: { label: '🟢 Открыт', color: '#4caf50' },
    in_progress: { label: '🟡 В работе', color: '#ff9800' },
    review: { label: '🔵 На проверке', color: '#2196f3' },
    completed: { label: '✅ Завершён', color: '#4caf50' },
    cancelled: { label: '❌ Отменён', color: '#f44336' },
  };
  const status = statusMap[order.status] || { label: order.status, color: '#999' };

  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 12, padding: 16, marginBottom: 12,
        cursor: 'pointer', transition: 'transform 0.1s',
        border: '1px solid var(--tg-theme-hint-color, #999)22',
      }}
      onMouseDown={e => e.currentTarget.style.transform = 'scale(0.98)'}
      onMouseUp={e => e.currentTarget.style.transform = ''}
      onMouseLeave={e => e.currentTarget.style.transform = ''}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--tg-theme-text-color, #000)' }}>
          {order.title}
        </h3>
        <Badge color={status.color}>{status.label}</Badge>
      </div>
      <p style={{ margin: '4px 0', fontSize: 14, opacity: 0.7, lineHeight: 1.4 }}>
        {order.description?.length > 120 ? order.description.slice(0, 120) + '...' : order.description}
      </p>
      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 13, opacity: 0.6 }}>
        {order.budget > 0 && <span>💰 {order.budget.toLocaleString('ru-RU')} ₽</span>}
        {order.applications_count !== undefined && <span>📩 {order.applications_count} откликов</span>}
        {order.employer_name && <span>🏢 {order.employer_name}</span>}
      </div>
    </div>
  );
}

export function SpecialistCard({ spec, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 12, padding: 16, marginBottom: 12,
        cursor: 'pointer',
        border: '1px solid var(--tg-theme-hint-color, #999)22',
      }}
    >
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <Avatar telegramId={spec.telegram_id} name={spec.full_name} size={48} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{spec.full_name}</div>
          <Stars rating={spec.rating} count={spec.rating_count} />
        </div>
        {spec.hourly_rate > 0 && (
          <div style={{ fontWeight: 600, color: 'var(--tg-theme-button-color, #3390ec)' }}>
            {spec.hourly_rate} ₽/ч
          </div>
        )}
      </div>
      {spec.skills && (
        <div style={{ marginTop: 8, fontSize: 13, opacity: 0.7 }}>
          🛠 {spec.skills}
        </div>
      )}
      <div style={{ marginTop: 4, fontSize: 13, opacity: 0.5 }}>
        ✅ {spec.completed_jobs} заказов
      </div>
    </div>
  );
}

export function EmptyState({ icon, text }) {
  return (
    <div style={{
      textAlign: 'center', padding: '48px 24px', opacity: 0.5,
      color: 'var(--tg-theme-text-color, #000)',
    }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 16 }}>{text}</div>
    </div>
  );
}

export function Loader() {
  return (
    <div style={{ textAlign: 'center', padding: 32, opacity: 0.5 }}>
      <div style={{ fontSize: 24 }}>⏳</div>
    </div>
  );
}
