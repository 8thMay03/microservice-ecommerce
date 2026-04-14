import { useState, useEffect, useCallback } from "react";
import { catalogApi } from "../api/catalog";

function flattenCategories(arr) {
  return arr.flatMap((c) => [c, ...(c.children?.length ? flattenCategories(c.children) : [])]);
}

const FALLBACK = [
  { id: "all", name: "All", slug: "all" },
];

export function useCatalog() {
  const [categories, setCategories] = useState([{ id: "all", name: "All", slug: "all" }]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw = await catalogApi.listCategories();
      const arr = Array.isArray(raw) ? raw : [];
      const flat = flattenCategories(arr);
      setCategories([{ id: "all", name: "All", slug: "all" }, ...flat]);
    } catch (err) {
      setError(err.message);
      setCategories(FALLBACK);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  return { categories, loading, error, refetch: fetchCategories };
}
