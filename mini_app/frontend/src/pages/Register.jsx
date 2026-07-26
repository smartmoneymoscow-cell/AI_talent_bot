import React, { useState } from 'react';
import { api } from '../api';

export function RegisterPage({ onRegistered }) {
  const [step, setStep] = useState(0);
  const [role, setRole] = useState('');
  const [fullName, setFullName] = useState('');
  const [bio, setBio] = useState('');
  const [skills, setSkills] = useState('');
  const [portfolio, setPortfolio] = useState('');
  const [rate, setRate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!fullName.trim() || fullName.trim().length < 2) {
      alert('Введите имя (минимум 2 символа)');
      return;
    }
    setSubmitting(true);
    try {
      await api.register({
        role,
        full_name: fullName.trim(),
        bio: bio.trim(),
        skills: skills.trim(),
        portfolio_url: portfolio.trim(),
        hourly_rate: rate ? parseInt(rate) : 0,
      });
      onRegistered();
    } catch (e) {
      alert(e.message || 'Ошибка регистрации');
    } finally {
      setSubmitting(false);
    }
  }

  const btnStyle = {
    padding: '14px 24px', borderRadius: 12, border: 'none',
    background: 'var(--tg-theme-button-color, #3390ec)', color: '#fff',
    cursor: 'pointer', fontSize: 15, fontWeight: 600, width: '100%',
  };
  const inputStyle = {
    width: '100%', padding: '12px 14px', borderRadius: 10,
    border: '1px solid var(--tg-theme-hint-color, #999)44',
    background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
    color: 'var(--tg-theme-text-color, #000)', fontSize: 15,
    boxSizing: 'border-box',
  };
  const labelStyle = {
    display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, marginTop: 16,
  };

  // Step 0: Role selection
  if (step === 0) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>🤖</div>
        <h2 style={{ margin: '0 0 8px' }}>AI Talent Hub</h2>
        <p style={{ opacity: 0.6, marginBottom: 32 }}>
          Платформа для предпринимателей и специалистов по ИИ
        </p>
        <p style={{ fontWeight: 600, marginBottom: 16 }}>Выберите роль:</p>
        <button
          onClick={() => { setRole('employer'); setStep(1); }}
          style={{ ...btnStyle, marginBottom: 12, background: '#4caf50' }}
        >
          🏢 Я предприниматель
        </button>
        <button
          onClick={() => { setRole('specialist'); setStep(1); }}
          style={btnStyle}
        >
          🧠 Я специалист по ИИ
        </button>
      </div>
    );
  }

  // Step 1: Name
  if (step === 1) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={() => setStep(0)} style={backBtn}>← Назад</button>
        <h2 style={{ margin: '0 0 16px' }}>👤 Как вас зовут?</h2>
        <input
          value={fullName} onChange={e => setFullName(e.target.value)}
          placeholder="ФИО или имя" style={inputStyle} autoFocus
          onKeyDown={e => e.key === 'Enter' && fullName.trim().length >= 2 && setStep(2)}
        />
        <button
          onClick={() => setStep(2)}
          disabled={fullName.trim().length < 2}
          style={{ ...btnStyle, marginTop: 16, opacity: fullName.trim().length < 2 ? 0.5 : 1 }}
        >
          Далее →
        </button>
      </div>
    );
  }

  // Step 2: Bio
  if (step === 2) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={() => setStep(1)} style={backBtn}>← Назад</button>
        <h2 style={{ margin: '0 0 16px' }}>
          {role === 'employer' ? '📝 О себе и бизнесе' : '🧠 О себе'}
        </h2>
        <textarea
          value={bio} onChange={e => setBio(e.target.value)} rows={4}
          placeholder={role === 'employer'
            ? 'Расскажите о вашем бизнесе...'
            : 'Опыт, специализация, достижения в ИИ...'}
          style={{ ...inputStyle, resize: 'vertical', minHeight: 100 }}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={() => setStep(role === 'specialist' ? 3 : 99)} style={btnStyle}>
            {role === 'specialist' ? 'Далее →' : 'Завершить ✅'}
          </button>
          <button onClick={() => { setBio(''); setStep(role === 'specialist' ? 3 : 99); }}
            style={{ ...btnStyle, background: 'var(--tg-theme-hint-color, #999)33', color: 'var(--tg-theme-text-color, #000)' }}>
            Пропустить
          </button>
        </div>
      </div>
    );
  }

  // Step 3: Skills (specialist only)
  if (step === 3) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={() => setStep(2)} style={backBtn}>← Назад</button>
        <h2 style={{ margin: '0 0 16px' }}>🛠 Навыки</h2>
        <input
          value={skills} onChange={e => setSkills(e.target.value)}
          placeholder="Python, PyTorch, LLM, NLP" style={inputStyle}
          onKeyDown={e => e.key === 'Enter' && setStep(4)}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={() => setStep(4)} style={btnStyle}>Далее →</button>
          <button onClick={() => { setSkills(''); setStep(4); }}
            style={{ ...btnStyle, background: 'var(--tg-theme-hint-color, #999)33', color: 'var(--tg-theme-text-color, #000)' }}>
            Пропустить
          </button>
        </div>
      </div>
    );
  }

  // Step 4: Portfolio
  if (step === 4) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={() => setStep(3)} style={backBtn}>← Назад</button>
        <h2 style={{ margin: '0 0 16px' }}>🔗 Портфолио</h2>
        <input
          value={portfolio} onChange={e => setPortfolio(e.target.value)}
          placeholder="https://github.com/..." style={inputStyle}
          onKeyDown={e => e.key === 'Enter' && setStep(5)}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={() => setStep(5)} style={btnStyle}>Далее →</button>
          <button onClick={() => { setPortfolio(''); setStep(5); }}
            style={{ ...btnStyle, background: 'var(--tg-theme-hint-color, #999)33', color: 'var(--tg-theme-text-color, #000)' }}>
            Пропустить
          </button>
        </div>
      </div>
    );
  }

  // Step 5: Rate (specialist only)
  if (step === 5) {
    return (
      <div style={{ padding: 24 }}>
        <button onClick={() => setStep(4)} style={backBtn}>← Назад</button>
        <h2 style={{ margin: '0 0 16px' }}>💰 Ставка (₽/час)</h2>
        <input
          type="number" value={rate} onChange={e => setRate(e.target.value)}
          placeholder="2000" style={inputStyle}
          onKeyDown={e => e.key === 'Enter' && setStep(99)}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button onClick={() => setStep(99)} style={btnStyle}>Завершить ✅</button>
          <button onClick={() => { setRate('0'); setStep(99); }}
            style={{ ...btnStyle, background: 'var(--tg-theme-hint-color, #999)33', color: 'var(--tg-theme-text-color, #000)' }}>
            Пропустить
          </button>
        </div>
      </div>
    );
  }

  // Step 99: Confirm & submit
  return (
    <div style={{ padding: 24 }}>
      <button onClick={() => setStep(role === 'specialist' ? 5 : 2)} style={backBtn}>← Назад</button>
      <h2 style={{ margin: '0 0 16px' }}>✅ Подтверждение</h2>
      <div style={{
        background: 'var(--tg-theme-secondary-bg-color, #f4f4f5)',
        borderRadius: 12, padding: 16, marginBottom: 16,
      }}>
        <p><b>Роль:</b> {role === 'employer' ? '🏢 Предприниматель' : '🧠 Специалист'}</p>
        <p><b>Имя:</b> {fullName}</p>
        {bio && <p><b>О себе:</b> {bio}</p>}
        {role === 'specialist' && skills && <p><b>Навыки:</b> {skills}</p>}
        {role === 'specialist' && portfolio && <p><b>Портфолио:</b> {portfolio}</p>}
        {role === 'specialist' && rate && <p><b>Ставка:</b> {rate} ₽/час</p>}
      </div>
      <button
        onClick={handleSubmit} disabled={submitting}
        style={{ ...btnStyle, opacity: submitting ? 0.6 : 1 }}
      >
        {submitting ? '⏳ Регистрация...' : '🎉 Зарегистрироваться'}
      </button>
    </div>
  );
}

const backBtn = {
  background: 'none', border: 'none',
  color: 'var(--tg-theme-button-color, #3390ec)',
  cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 16,
};
