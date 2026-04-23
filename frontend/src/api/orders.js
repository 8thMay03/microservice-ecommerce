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

export const ordersApi = {
  create: (payload, token) =>
    request("/api/orders/", {
      method: "POST",
      body: JSON.stringify(payload),
    }, token),

  list: (customer_id, token) =>
    request(`/api/orders/?customer_id=${customer_id}`, {}, token),

  get: (id, token) =>
    request(`/api/orders/${id}/`, {}, token),
};

export const cartApi = {
  get: (customer_id, token) =>
    request(`/api/cart/${customer_id}/`, {}, token),

  addItem: (customer_id, { product_id, quantity, unit_price }, token) =>
    request(`/api/cart/${customer_id}/items/`, {
      method: "POST",
      body: JSON.stringify({ product_id, quantity, unit_price }),
    }, token),

  clear: (customer_id, token) =>
    request(`/api/cart/${customer_id}/clear/`, { method: "DELETE" }, token),
};
