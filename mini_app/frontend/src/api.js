/**
 * API клиент для Mini App
 */
const API_BASE = '/api';

function getInitData() {
  return window.Telegram?.WebApp?.initData || '';
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
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
