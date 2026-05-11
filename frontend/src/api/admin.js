async function request(url, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  const data = res.status === 204 ? {} : await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail =
      data.detail || data.error ||
      Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`).join(" · ") ||
      `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

export const adminOrdersApi = {
  listAll: (token) => request("/api/orders/", {}, token),
  get: (id, token) => request(`/api/orders/${id}/`, {}, token),
  updateStatus: (id, status, token) =>
    request(`/api/orders/${id}/`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }, token),
};

export const adminUsersApi = {
  list: (token) => request("/api/users/", {}, token),
  listByRole: (role, token) => request(`/api/users/?role=${role}`, {}, token),
  get: (id, token) => request(`/api/users/${id}/`, {}, token),
  update: (id, data, token) =>
    request(`/api/users/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
  deactivate: (id, token) =>
    request(`/api/users/${id}/`, { method: "DELETE" }, token),
};

export const adminStaffApi = {
  list: (token) => request("/api/users/?role=STAFF", {}, token),
  get: (id, token) => request(`/api/users/${id}/`, {}, token),
  create: (data, token) =>
    request("/api/users/register/", {
      method: "POST",
      body: JSON.stringify(data),
    }, token),
  update: (id, data, token) =>
    request(`/api/users/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
  deactivate: (id, token) =>
    request(`/api/users/${id}/`, { method: "DELETE" }, token),
};

export const adminAnalyticsApi = {
  overview: (token) =>
    request("/api/recommendations/analytics/overview/", {}, token),
};
