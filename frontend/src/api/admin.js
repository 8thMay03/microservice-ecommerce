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

export const adminCustomersApi = {
  list: (token) => request("/api/customers/", {}, token),
  get: (id, token) => request(`/api/customers/${id}/`, {}, token),
  update: (id, data, token) =>
    request(`/api/customers/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
  deactivate: (id, token) =>
    request(`/api/customers/${id}/`, { method: "DELETE" }, token),
};

export const adminStaffApi = {
  list: (token) => request("/api/staff/", {}, token),
  get: (id, token) => request(`/api/staff/${id}/`, {}, token),
  create: (data, token) =>
    request("/api/staff/register/", {
      method: "POST",
      body: JSON.stringify(data),
    }, token),
  update: (id, data, token) =>
    request(`/api/staff/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }, token),
  deactivate: (id, token) =>
    request(`/api/staff/${id}/`, { method: "DELETE" }, token),
};
