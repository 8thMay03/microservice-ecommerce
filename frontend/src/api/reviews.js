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
  getComments: (bookId) =>
    request(`${BASE}/comments/?book_id=${bookId}`),

  postComment: ({ book_id, customer_id, content }, token) =>
    request(`${BASE}/comments/`, {
      method: "POST",
      body: JSON.stringify({ book_id, customer_id, content }),
    }, token),

  deleteComment: (id, token) =>
    request(`${BASE}/comments/${id}/`, { method: "DELETE" }, token),

  getRatingSummary: (bookId) =>
    request(`${BASE}/ratings/book/${bookId}/summary/`),

  getMyRating: (bookId, customerId) =>
    request(`${BASE}/ratings/?book_id=${bookId}&customer_id=${customerId}`),

  postRating: ({ book_id, customer_id, score }, token) =>
    request(`${BASE}/ratings/`, {
      method: "POST",
      body: JSON.stringify({ book_id, customer_id, score }),
    }, token),
};
