import { useState, useEffect, useCallback } from "react";
import { productsApi } from "../api/products";
import { normalizeProduct } from "../utils/productUtils";

function toDisplayProduct(p) {
  return {
    id: p.id,
    title: p.title,
    brand: p.brand || "",
    author: p.author || p.brand || "",
    price: Number(p.price),
    image: p.image || p.cover_image,
    isNew: p.isNew ?? true,
    rating: p.rating ?? null,
    reviewCount: p.reviewCount ?? p.review_count ?? null,
    category_id: p.category_id ?? p.category,
    description: p.description || "",
    product_type: p.product_type || "BOOK",
    sku: p.sku || "",
    attributes: p.attributes || {},
    pages: p.pages,
    isbn: p.isbn,
    published_date: p.published_date || p.year,
    language: p.language,
  };
}

export function useProducts(params = {}) {
  const [data, setData] = useState({ results: [], total: 0, page: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProducts = useCallback(async (opts = {}) => {
    setLoading(true);
    setError(null);
    try {
      const merged = { ...params, ...opts };
      if (merged.category_id === "all" || merged.category_id == null) delete merged.category_id;
      const res = await productsApi.list(merged);
      setData({
        results: (res.results || []).map(normalizeProduct).filter(Boolean),
        total: res.total ?? 0,
        page: res.page ?? 1,
        pageSize: res.page_size ?? 20,
      });
    } catch (err) {
      setError(err.message);
      setData({
        results: [],
        total: 0,
        page: 1,
        pageSize: 20,
      });
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(params)]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  return { ...data, loading, error, refetch: fetchProducts };
}
