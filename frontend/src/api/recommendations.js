const BASE = "/api/recommendations";

/**
 * Get product recommendations for a customer.
 * @param {number} customerId - Customer ID; use 0 for guest (returns popular picks).
 * @param {{ limit?: number }} options
 * @returns {Promise<{ recommendations: Array<{ product_id, title, brand, price, cover_image, category_id, product_type }> }>}
 */
export async function getRecommendations(customerId, options = {}) {
  const limit = options.limit ?? 8;
  const url = `${BASE}/${customerId}/?limit=${limit}`;
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || data.detail || `HTTP ${res.status}`);
  }
  return data;
}
