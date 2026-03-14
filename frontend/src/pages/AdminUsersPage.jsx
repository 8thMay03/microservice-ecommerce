import { useState, useEffect, useCallback } from "react";
import {
  Users, Loader2, AlertCircle, RefreshCw, Search,
  Mail, Phone, MapPin, Trash2, Calendar,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { adminCustomersApi } from "../api/admin";

export default function AdminUsersPage() {
  const { user, token, isAuthenticated } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  const isAdmin = user?.role === "manager";

  const fetchCustomers = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await adminCustomersApi.list(token);
      setCustomers(Array.isArray(data) ? data : data.results ?? []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { if (token) fetchCustomers(); }, [fetchCustomers, token]);

  const handleDeactivate = async (id) => {
    if (!confirm("Deactivate this user?")) return;
    try {
      await adminCustomersApi.deactivate(id, token);
      setCustomers((prev) => prev.filter((c) => c.id !== id));
    } catch { /* ignore */ }
  };

  const filtered = customers.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return c.first_name?.toLowerCase().includes(q) || c.last_name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) || String(c.id).includes(q);
  });

  if (!isAuthenticated || !isAdmin) {
    return (<><Navbar /><div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
      <Users size={40} className="text-gray-300 mb-4" /><h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Admin Access Required</h1></div></>);
  }

  return (
    <><Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 animate-fade-up">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">User Management</h1>
              <p className="text-sm text-gray-500 mt-1">{customers.length} registered user{customers.length !== 1 ? "s" : ""}</p>
            </div>
            <button onClick={fetchCustomers} disabled={loading}
              className="p-2.5 rounded-xl border border-gray-200 bg-white text-gray-500 hover:text-gray-900 transition-colors disabled:opacity-50">
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Search */}
          <div className="flex items-center bg-white border border-gray-200 rounded-full px-4 py-2 gap-2 max-w-sm mb-6">
            <Search size={14} className="text-gray-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name, email, ID…"
              className="bg-transparent text-sm outline-none flex-1 text-gray-900 placeholder-gray-400" />
          </div>

          {error && <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700"><AlertCircle size={16} />{error}</div>}

          {loading && customers.length === 0 ? (
            <div className="flex justify-center py-20"><Loader2 size={28} className="animate-spin text-gray-400" /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-gray-400"><Users size={28} className="mx-auto mb-2 opacity-50" /><p className="text-sm">No users found.</p></div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      <th className="px-5 py-3">ID</th>
                      <th className="px-5 py-3">Name</th>
                      <th className="px-5 py-3">Email</th>
                      <th className="px-5 py-3">Phone</th>
                      <th className="px-5 py-3">Joined</th>
                      <th className="px-5 py-3 w-12"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((c) => {
                      const date = new Date(c.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
                      return (
                        <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                          <td className="px-5 py-3 text-gray-500 font-mono text-xs">#{c.id}</td>
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 text-xs font-semibold flex items-center justify-center shrink-0">
                                {(c.first_name || "?").charAt(0).toUpperCase()}
                              </div>
                              <span className="font-medium text-gray-900">{c.first_name} {c.last_name}</span>
                            </div>
                          </td>
                          <td className="px-5 py-3 text-gray-600">{c.email}</td>
                          <td className="px-5 py-3 text-gray-600">{c.phone || "—"}</td>
                          <td className="px-5 py-3 text-gray-500 text-xs">{date}</td>
                          <td className="px-5 py-3">
                            <button onClick={() => handleDeactivate(c.id)} className="p-1.5 text-gray-400 hover:text-red-500 transition-colors" title="Deactivate">
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
