import React, { useState, useEffect } from 'react';
import { useApp } from '../context';
import { api } from '../api';
import { Stars, EmptyState, Loader } from '../components';

export function ReviewsPage() {
  const { user } = useApp();
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getReviews().then(setReviews).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: '0 0 16px', fontSize: 18 }}>
        ⭐ Отзывы о вас
      </h2>
      {reviews.length === 0 ? (
        <EmptyState icon="⭐" text="Пока нет отзывов" />
      ) : (
        reviews.map(r => (
          <div key={r.id} style={{
            background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
            borderRadius: 12, padding: 16, marginBottom: 12,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 15 }}>{r.reviewer_name}</span>
              <Stars rating={r.rating} count={0} />
            </div>
            <div style={{ fontSize: 13, opacity: 0.6, marginBottom: 4 }}>
              📦 Заказ: {r.order_title}
            </div>
            {r.comment && (
              <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>{r.comment}</p>
            )}
          </div>
        ))
      )}
    </div>
  );
}
