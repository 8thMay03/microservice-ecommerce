const BASE = "/api/reviews";

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

export const reviewsApi = {
  getComments: (productId) =>
    request(`${BASE}/comments/?product_id=${productId}`),

  postComment: ({ product_id, customer_id, customer_name, content }, token) =>
    request(`${BASE}/comments/`, {
      method: "POST",
      body: JSON.stringify({ product_id, customer_id, customer_name, content }),
    }, token),

  updateComment: (id, { content }, token) =>
    request(`${BASE}/comments/${id}/`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }, token),

  deleteComment: (id, token) =>
    request(`${BASE}/comments/${id}/`, { method: "DELETE" }, token),

  getRatingSummary: (productId) =>
    request(`${BASE}/ratings/product/${productId}/summary/`),

  getMyRating: (productId, customerId) =>
    request(`${BASE}/ratings/?product_id=${productId}&customer_id=${customerId}`),

  postRating: ({ product_id, customer_id, score }, token) =>
    request(`${BASE}/ratings/`, {
      method: "POST",
      body: JSON.stringify({ product_id, customer_id, score }),
    }, token),
};
