import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context';
import { api } from '../api';
import { Avatar, Stars, Loader } from '../components';

export function SpecialistProfilePage() {
  const { user, refreshUser } = useApp();
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState(user?.bio || '');
  const [skills, setSkills] = useState(user?.skills || '');
  const [portfolio, setPortfolio] = useState(user?.portfolio_url || '');
  const [rate, setRate] = useState(user?.hourly_rate?.toString() || '');
  const [saving, setSaving] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [stats, setStats] = useState(null);
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    api.getMyStats().then(setStats).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await api.updateMe({
        bio, skills,
        portfolio_url: portfolio,
        hourly_rate: rate ? parseInt(rate) : 0,
      });
      await refreshUser();
      setEditing(false);
    } catch (e) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function startVoiceInput(field) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = e => chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        // Отправляем в бот для распознавания — через Telegram WebApp
        const tg = window.Telegram?.WebApp;
        if (tg) {
          tg.showAlert('🎤 Голосовое записано! Отправьте его боту для распознавания.');
        }
      };

      recorder.start();
      setRecording(true);

      // Автостоп через 30 сек
      setTimeout(() => {
        if (recorder.state === 'recording') recorder.stop();
        setRecording(false);
      }, 30000);
    } catch (e) {
      alert('Микрофон не доступен');
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }

  async function handleSwitchRole() {
    if (!confirm('Сменить роль на «Предприниматель»?')) return;
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
      {/* Шапка профиля */}
      <div style={{
        textAlign: 'center', padding: '24px 16px', marginBottom: 16,
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 16,
      }}>
        <Avatar telegramId={user.telegram_id} name={user.full_name} size={80} />
        <h2 style={{ margin: '12px 0 4px', fontSize: 20 }}>{user.full_name}</h2>
        {user.username && (
          <div style={{ fontSize: 14, opacity: 0.5 }}>@{user.username}</div>
        )}
        <div style={{ marginTop: 8 }}>
          <Stars rating={user.rating} count={user.rating_count} />
        </div>
        {user.hourly_rate > 0 && (
          <div style={{ marginTop: 8, fontWeight: 600, color: 'var(--tg-theme-button-color, #3390ec)' }}>
            💰 {user.hourly_rate} ₽/час
          </div>
        )}
      </div>

      {/* Статистика */}
      {stats && (
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16,
        }}>
          {[
            { label: 'Заказов', value: stats.completed_jobs || 0, icon: '✅' },
            { label: 'Откликов', value: stats.total_applications || 0, icon: '📩' },
            { label: 'Принято', value: stats.accepted_applications || 0, icon: '🎉' },
            { label: 'Заработано', value: `${((stats.total_earned || 0) / 100).toLocaleString('ru-RU')} ₽`, icon: '💰' },
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

      {/* Описание / Редактирование */}
      {editing ? (
        <div>
          <label style={labelStyle}>О себе</label>
          <div style={{ position: 'relative' }}>
            <textarea
              value={bio} onChange={e => setBio(e.target.value)} rows={4}
              style={textareaStyle}
              placeholder="Опыт, специализация, достижения..."
            />
            <button onClick={() => startVoiceInput('bio')} style={voiceBtnStyle}>
              {recording ? '⏹' : '🎤'}
            </button>
          </div>

          <label style={labelStyle}>Навыки</label>
          <input value={skills} onChange={e => setSkills(e.target.value)}
            placeholder="Python, PyTorch, LLM..." style={inputStyle} />

          <label style={labelStyle}>Портфолио</label>
          <input value={portfolio} onChange={e => setPortfolio(e.target.value)}
            placeholder="https://github.com/..." style={inputStyle} />

          <label style={labelStyle}>Ставка (₽/час)</label>
          <input type="number" value={rate} onChange={e => setRate(e.target.value)}
            placeholder="2000" style={inputStyle} />

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
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
            <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🧠 О себе</h3>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>
              {user.bio || 'Не заполнено'}
            </p>
          </div>

          {user.skills && (
            <div style={{
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              borderRadius: 12, padding: 16, marginBottom: 12,
            }}>
              <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🛠 Навыки</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {user.skills.split(',').map(s => s.trim()).filter(Boolean).map(s => (
                  <span key={s} style={{
                    padding: '4px 10px', borderRadius: 8, fontSize: 13,
                    background: 'var(--tg-theme-button-color, #3390ec)22',
                    color: 'var(--tg-theme-button-color, #3390ec)',
                  }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {user.portfolio_url && (
            <div style={{
              background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
              borderRadius: 12, padding: 16, marginBottom: 12,
            }}>
              <h3 style={{ margin: '0 0 8px', fontSize: 15 }}>🔗 Портфолио</h3>
              <a href={user.portfolio_url} target="_blank" rel="noopener"
                style={{ color: 'var(--tg-theme-button-color, #3390ec)', fontSize: 14 }}>
                {user.portfolio_url}
              </a>
            </div>
          )}

          <button onClick={() => {
            setBio(user.bio || '');
            setSkills(user.skills || '');
            setPortfolio(user.portfolio_url || '');
            setRate(user.hourly_rate?.toString() || '');
            setEditing(true);
          }} style={{ ...primaryBtn, width: '100%', marginBottom: 12 }}>
            ✏️ Редактировать профиль
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
            {switching ? '⏳...' : '🔄 Сменить роль на предпринимателя'}
          </button>
        </div>
      )}
    </div>
  );
}

const labelStyle = {
  display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 4, marginTop: 12,
  color: 'var(--tg-theme-text-color, #000)',
};
const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #99944',
  background: 'var(--tg-theme-bg-color, #fff)',
  color: 'var(--tg-theme-text-color, #000)', fontSize: 14, boxSizing: 'border-box',
};
const textareaStyle = {
  ...inputStyle, resize: 'vertical', minHeight: 80,
};
const primaryBtn = {
  padding: '12px 24px', borderRadius: 10, border: 'none',
  background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
  cursor: 'pointer', fontSize: 14, fontWeight: 600,
};
const secondaryBtn = {
  ...primaryBtn, background: 'var(--tg-theme-hint-color, #999)33',
  color: 'var(--tg-theme-text-color, #000)',
};
const voiceBtnStyle = {
  position: 'absolute', right: 8, bottom: 8,
  width: 36, height: 36, borderRadius: '50%', border: 'none',
  background: recording ? '#f44336' : 'var(--tg-theme-button-color, #3390ec)',
  color: '#fff', cursor: 'pointer', fontSize: 16,
};
