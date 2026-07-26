import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { SpecialistCard, Avatar, Stars, EmptyState, Loader } from '../components';

export function SpecialistsPage() {
  const [specialists, setSpecialists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [minRating, setMinRating] = useState('');
  const [maxRate, setMaxRate] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => { load(); }, []);

  async function load(params = {}) {
    setLoading(true);
    try {
      const data = await api.getSpecialists({
        search: search || undefined,
        min_rating: minRating || undefined,
        max_rate: maxRate || undefined,
        ...params,
      });
      setSpecialists(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }

  function handleSearch(e) {
    e.preventDefault();
    load();
  }

  if (selected) {
    return <SpecialistDetail spec={selected} onBack={() => { setSelected(null); load(); }} />;
  }

  return (
    <div style={{ padding: 16 }}>
      <form onSubmit={handleSearch} style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text" placeholder="🔍 Поиск по имени, навыкам..."
            value={search} onChange={e => setSearch(e.target.value)}
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 10,
              border: '1px solid #99944',
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              color: 'var(--tg-theme-text-color, #000)', fontSize: 14,
            }}
          />
          <button type="button" onClick={() => setShowFilters(!showFilters)} style={{
            padding: '10px 14px', borderRadius: 10, border: 'none',
            background: showFilters ? 'var(--tg-theme-button-color, #3390ec)' : 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
            color: showFilters ? '#fff' : 'var(--tg-theme-text-color, #000)',
            cursor: 'pointer', fontSize: 16,
          }}>
            ⚙️
          </button>
        </div>

        {showFilters && (
          <div style={{
            marginTop: 8, padding: 12, borderRadius: 10,
            background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <input type="number" placeholder="Рейтинг от (1-5)" value={minRating}
                onChange={e => setMinRating(e.target.value)} style={filterInput} />
              <input type="number" placeholder="Ставка до (₽/ч)" value={maxRate}
                onChange={e => setMaxRate(e.target.value)} style={filterInput} />
            </div>
            <button type="submit" style={{
              width: '100%', padding: '8px 0', borderRadius: 8, border: 'none',
              background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
              cursor: 'pointer', fontSize: 14, fontWeight: 600,
            }}>
              Применить
            </button>
          </div>
        )}
      </form>

      {loading ? <Loader /> : specialists.length === 0 ? (
        <EmptyState icon="🔍" text="Специалисты не найдены" />
      ) : (
        specialists.map(s => (
          <SpecialistCard key={s.id} spec={s} onClick={() => setSelected(s)} />
        ))
      )}
    </div>
  );
}


function SpecialistDetail({ spec, onBack }) {
  const [data, setData] = useState(spec);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSpecialist(spec.id).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [spec.id]);

  return (
    <div style={{ padding: 16 }}>
      <button onClick={onBack} style={{
        background: 'none', border: 'none', color: 'var(--tg-theme-button-color, #3390ec)',
        cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 12,
      }}>
        ← Назад
      </button>

      {/* Шапка */}
      <div style={{
        textAlign: 'center', padding: '24px 16px', marginBottom: 16,
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)', borderRadius: 16,
      }}>
        <Avatar telegramId={spec.telegram_id} name={spec.full_name} size={80} />
        <h2 style={{ margin: '12px 0 4px' }}>{spec.full_name}</h2>
        {spec.username && <div style={{ fontSize: 14, opacity: 0.5 }}>@{spec.username}</div>}
        <div style={{ marginTop: 8 }}><Stars rating={spec.rating} count={spec.rating_count} /></div>
        {spec.hourly_rate > 0 && (
          <div style={{ marginTop: 8, fontWeight: 600, color: 'var(--tg-theme-button-color, #3390ec)' }}>
            💰 {spec.hourly_rate} ₽/час
          </div>
        )}
        <div style={{ marginTop: 4, fontSize: 13, opacity: 0.5 }}>
          ✅ {spec.completed_jobs} выполнено
        </div>
      </div>

      {/* Описание */}
      {spec.bio && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          borderRadius: 12, padding: 16, marginBottom: 12,
        }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🧠 О себе</h3>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>{spec.bio}</p>
        </div>
      )}

      {/* Навыки */}
      {spec.skills && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          borderRadius: 12, padding: 16, marginBottom: 12,
        }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🛠 Навыки</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {spec.skills.split(',').map(s => s.trim()).filter(Boolean).map(s => (
              <span key={s} style={{
                padding: '4px 10px', borderRadius: 8, fontSize: 13,
                background: 'var(--tg-theme-button-color, #3390ec)22',
                color: 'var(--tg-theme-button-color, #3390ec)',
              }}>{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Портфолио */}
      {spec.portfolio_url && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          borderRadius: 12, padding: 16, marginBottom: 12,
        }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🔗 Портфолио</h3>
          <a href={spec.portfolio_url} target="_blank" rel="noopener"
            style={{ color: 'var(--tg-theme-button-color, #3390ec)', fontSize: 14 }}>
            {spec.portfolio_url}
          </a>
        </div>
      )}

      {/* Отзывы */}
      {data.reviews?.length > 0 && (
        <div style={{
          background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
          borderRadius: 12, padding: 16,
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>⭐ Отзывы</h3>
          {data.reviews.map(r => (
            <div key={r.id} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: '1px solid #99922' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{r.reviewer_name}</span>
                <span>{'⭐'.repeat(r.rating)}</span>
              </div>
              {r.comment && <p style={{ margin: 0, fontSize: 13, opacity: 0.7 }}>{r.comment}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const filterInput = {
  flex: 1, padding: '8px 10px', borderRadius: 8, border: '1px solid #99944',
  background: 'var(--tg-theme-bg-color, #fff)',
  color: 'var(--tg-theme-text-color, #000)', fontSize: 13,
};
