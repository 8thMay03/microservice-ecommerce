async function request(url, options = {}, token = null) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  const data = res.status === 204 ? {} : await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail =
      data.detail ||
      data.error ||
      data.non_field_errors?.[0] ||
      Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v[0] : v}`)
        .join(" · ") ||
      `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

export const ragApi = {
  /**
   * Send a chat message to the RAG service.
   * @param {string} message - User's question
   * @param {object} [opts]
   * @param {string|null} [opts.token] - JWT access token (optional)
   * @param {number|null} [opts.customerId] - Customer ID for personalisation (optional)
   */
  chat: (message, { token = null, customerId = null } = {}) =>
    request(
      "/api/rag/chat",
      {
        method: "POST",
        body: JSON.stringify({
          message,
          ...(customerId ? { customer_id: customerId } : {}),
        }),
      },
      token,
    ),
};
