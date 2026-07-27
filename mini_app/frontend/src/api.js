/**
 * API клиент для Mini App
 */
const API_BASE = '/api';

function getInitData() {
  try {
    return window.Telegram?.WebApp?.initData || '';
  } catch (e) {
    return '';
  }
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const fetchTimeout = setTimeout(() => controller.abort(), 8000);

  const raceTimeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Превышено время ожидания')), 10000)
  );

  const initData = getInitData();

  try {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    // Only send initData header if we have it
    if (initData) {
      headers['X-Telegram-Init-Data'] = initData;
    }

    const fetchPromise = fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const res = await Promise.race([fetchPromise, raceTimeout]);
    clearTimeout(fetchTimeout);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  } catch (e) {
    clearTimeout(fetchTimeout);
    if (e.name === 'AbortError') {
      throw new Error('Превышено время ожидания');
    }
    throw e;
  }
}

export const api = {
  // Auth
  getMe: () => request('/me'),
  register: (data) => request('/register', { method: 'POST', body: data }),
  switchRole: () => request('/switch-role', { method: 'POST' }),
  updateMe: (data) => request('/me', { method: 'PATCH', body: data }),
  getMyStats: () => request('/me/stats'),

  // Orders
  getOrders: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/orders?${qs}`);
  },
  getOrder: (id) => request(`/orders/${id}`),
  createOrder: (data) => request('/orders', { method: 'POST', body: data }),
  updateOrderStatus: (id, status) =>
    request(`/orders/${id}/status?status=${status}`, { method: 'PATCH' }),

  // Applications
  getApplications: (orderId) => request(`/orders/${orderId}/applications`),
  getMyApplications: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/my-applications?${qs}`);
  },
  createApplication: (data) => request('/applications', { method: 'POST', body: data }),
  acceptApplication: (id) => request(`/applications/${id}/accept`, { method: 'PATCH' }),
  rejectApplication: (id) => request(`/applications/${id}/reject`, { method: 'PATCH' }),

  // Specialists
  getSpecialists: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/specialists?${qs}`);
  },
  getSpecialist: (id) => request(`/specialists/${id}`),

  // Reviews
  getReviews: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/reviews?${qs}`);
  },
  createReview: (data) => request('/reviews', { method: 'POST', body: data }),

  // Avatar
  getAvatar: (tgId) => request(`/avatar/${tgId}`),
};

/**
 * Get Telegram user data from initData (parsed by server or from WebApp)
 */
export function getTelegramUser() {
  try {
    const tg = window.Telegram?.WebApp;
    if (!tg) return null;

    const user = tg.initDataUnsafe?.user;
    if (user) {
      return {
        id: user.id,
        first_name: user.first_name,
        last_name: user.last_name || '',
        username: user.username || '',
        full_name: [user.first_name, user.last_name].filter(Boolean).join(' '),
      };
    }
  } catch (e) {
    console.warn('getTelegramUser error:', e);
  }
  return null;
}
