const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),
  dashboard: () => request('/api/dashboard'),
  alerts: (limit = 50) => request(`/api/alerts?limit=${limit}`),
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),
  person: (id) => request(`/api/persons/${id}`),
  transaction: (id) => request(`/api/transactions/${id}`),
  timeline: (personId) => request(`/api/persons/${personId}/timeline`),
  networkGraph: (limit = 150) => request(`/api/graph/network?node_limit=${limit}`),
  personGraph: (personId) => request(`/api/graph/person/${personId}`),
  fraudRings: () => request('/api/fraud/rings'),
  fraudPatterns: () => request('/api/fraud/patterns'),
};
