import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Plus, Pencil, Trash2, BookMarked, ArrowLeft, Loader2, AlertCircle, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { productsApi } from "../api/products";
import { catalogApi } from "../api/catalog";

export default function AdminProductsPage() {
  const { user, token, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null); // { mode: "create"|"edit", product?: {} }
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({});

  const canManage = user?.role === "manager" || user?.role === "staff";

  useEffect(() => {
    if (!isAuthenticated || !canManage) {
      navigate("/login", { state: { from: { pathname: "/admin/products" } } });
      return;
    }
    load();
  }, [isAuthenticated, canManage, navigate]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [productsRes, catRes] = await Promise.all([
        productsApi.list({}, token),
        catalogApi.listCategories(token).catch(() => []),
      ]);
      setProducts(productsRes.results || []);
      const raw = Array.isArray(catRes) ? catRes : [];
      const flatten = (arr) =>
        arr.flatMap((c) => [c, ...(c.children ? flatten(c.children) : [])]);
      setCategories(flatten(raw));
    } catch (err) {
      setError(err.message || "Failed to load products.");
    } finally {
      setLoading(false);
    }
  };

  const openCreate = () => {
    setForm({
      title: "",
      brand: "",
      sku: "",
      description: "",
      price: "",
      cover_image: "",
      category_id: categories[0]?.id ?? 1,
      published_date: "",
      language: "English",
      pages: "",
      is_active: true,
      stock_quantity: 0,
      warehouse_location: "",
    });
    setModal({ mode: "create" });
  };

  const openEdit = (product) => {
    setForm({
      title: product.title,
      brand: product.brand,
      sku: product.sku,
      description: product.description || "",
      price: String(product.price),
      cover_image: product.cover_image || "",
      category_id: product.category_id,
      published_date: product.attributes?.published_date || product.published_date || "",
      language: product.attributes?.language || product.language || "English",
      pages: product.attributes?.pages ? String(product.attributes.pages) : (product.pages ? String(product.pages) : ""),
      is_active: product.is_active ?? true,
      stock_quantity: product.inventory?.stock_quantity ?? 0,
      warehouse_location: product.inventory?.warehouse_location || "",
    });
    setModal({ mode: "edit", product });
  };

  const closeModal = () => setModal(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: form.title,
        brand: form.brand,
        sku: form.sku,
        description: form.description,
        price: parseFloat(form.price) || 0,
        cover_image: form.cover_image,
        category_id: parseInt(form.category_id, 10) || 1,
        published_date: form.published_date || null,
        language: form.language || "English",
        pages: form.pages ? parseInt(form.pages, 10) : null,
        is_active: form.is_active,
        stock_quantity: parseInt(form.stock_quantity, 10) || 0,
        warehouse_location: form.warehouse_location,
      };
      if (modal.mode === "create") {
        await productsApi.create(payload, token);
      } else {
        await productsApi.update(modal.product.id, payload, token);
      }
      closeModal();
      load();
    } catch (err) {
      setError(err.message || "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (product) => {
    if (!confirm(`Delete "${product.title}"? This will deactivate the product.`)) return;
    setError(null);
    try {
      await productsApi.delete(product.id, token);
      load();
    } catch (err) {
      setError(err.message || "Failed to delete.");
    }
  };

  const set = (field) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: v }));
  };

  if (!isAuthenticated || !canManage) return null;

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={18} />
              Back
            </Link>
            <Link to="/" className="flex items-center gap-2 text-gray-900">
              <BookMarked size={24} strokeWidth={1.8} />
              <span className="font-serif text-xl">Admin · Products</span>
            </Link>
          </div>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700 transition-colors"
          >
            <Plus size={16} />
            Add Product
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {error && (
          <div className="flex items-center justify-between gap-4 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700">
            <span className="flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
              <X size={16} />
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 size={32} className="animate-spin text-gray-400" />
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {products.length === 0 ? (
              <div className="py-16 text-center text-gray-500">
                <BookMarked size={48} className="mx-auto mb-4 text-gray-300" />
                <p className="font-medium">No products yet</p>
                <p className="text-sm mt-1">Add your first product to get started.</p>
                <button
                  onClick={openCreate}
                  className="mt-4 inline-flex items-center gap-2 bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-700"
                >
                  <Plus size={16} />
                  Add Product
                </button>
              </div>
            ) : (
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Title</th>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">brand</th>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Price</th>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Stock</th>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((p) => (
                    <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                      <td className="px-4 py-3 font-medium text-gray-900">{p.title}</td>
                      <td className="px-4 py-3 text-gray-600">{p.brand}</td>
                      <td className="px-4 py-3 text-gray-600">${Number(p.price).toFixed(2)}</td>
                      <td className="px-4 py-3 text-gray-600">{p.inventory?.stock_quantity ?? 0}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            p.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {p.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEdit(p)}
                            className="p-1.5 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                            title="Edit"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => handleDelete(p)}
                            className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="font-serif text-xl font-medium">
                {modal.mode === "create" ? "Add Product" : "Edit Product"}
              </h2>
              <button onClick={closeModal} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input
                  type="text"
                  value={form.title || ""}
                  onChange={set("title")}
                  required
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">brand *</label>
                <input
                  type="text"
                  value={form.brand || ""}
                  onChange={set("brand")}
                  required
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">sku *</label>
                <input
                  type="text"
                  value={form.sku || ""}
                  onChange={set("sku")}
                  required
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={form.description || ""}
                  onChange={set("description")}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Price *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price || ""}
                    onChange={set("price")}
                    required
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  {categories.length > 0 ? (
                    <select
                      value={form.category_id ?? ""}
                      onChange={set("category_id")}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      value={form.category_id ?? ""}
                      onChange={set("category_id")}
                      placeholder="Category ID (create category first)"
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                    />
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Pages</label>
                  <input
                    type="number"
                    min="0"
                    value={form.pages || ""}
                    onChange={set("pages")}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Stock</label>
                  <input
                    type="number"
                    min="0"
                    value={form.stock_quantity ?? ""}
                    onChange={set("stock_quantity")}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cover Image URL</label>
                <input
                  type="url"
                  value={form.cover_image || ""}
                  onChange={set("cover_image")}
                  placeholder="https://..."
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-gray-200 focus:border-gray-400"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active ?? true} onChange={set("is_active")} className="rounded" />
                <span className="text-sm text-gray-700">Active (visible to customers)</span>
              </label>
              <div className="flex justify-end gap-3 pt-4">
                <button type="button" onClick={closeModal} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-700 disabled:opacity-60"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : null}
                  {modal.mode === "create" ? "Create" : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
