import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList, Loader2, AlertCircle, RefreshCw, Search,
  ChevronDown, ChevronUp, MapPin, CreditCard, Package,
  Clock, CheckCircle2, XCircle, Truck,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { adminOrdersApi } from "../api/admin";

const STATUS_OPTIONS = ["PENDING", "CONFIRMED", "PAID", "SHIPPED", "DELIVERED", "CANCELLED", "REFUNDED"];

const STATUS_CFG = {
  PENDING:   { label: "Pending",   color: "bg-yellow-100 text-yellow-800", icon: Clock },
  CONFIRMED: { label: "Confirmed", color: "bg-blue-100 text-blue-800",     icon: CheckCircle2 },
  PAID:      { label: "Paid",      color: "bg-emerald-100 text-emerald-800", icon: CreditCard },
  SHIPPED:   { label: "Shipped",   color: "bg-indigo-100 text-indigo-800", icon: Truck },
  DELIVERED: { label: "Delivered", color: "bg-green-100 text-green-800",   icon: CheckCircle2 },
  CANCELLED: { label: "Cancelled", color: "bg-red-100 text-red-800",       icon: XCircle },
  REFUNDED:  { label: "Refunded",  color: "bg-gray-100 text-gray-800",     icon: RefreshCw },
};

function Badge({ status }) {
  const c = STATUS_CFG[status] || STATUS_CFG.PENDING;
  const Icon = c.icon;
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.color}`}><Icon size={12} />{c.label}</span>;
}

export default function AdminOrdersPage() {
  const { user, token, isAuthenticated } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [expanded, setExpanded] = useState(null);

  const isAdmin = user?.role === "manager";

  const fetchOrders = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await adminOrdersApi.listAll(token);
      setOrders(Array.isArray(data) ? data : data.results ?? []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { if (token) fetchOrders(); }, [fetchOrders, token]);

  const handleStatusChange = async (orderId, newStatus) => {
    try {
      const updated = await adminOrdersApi.updateStatus(orderId, newStatus, token);
      setOrders((prev) => prev.map((o) => o.id === orderId ? { ...o, ...updated } : o));
    } catch { /* ignore */ }
  };

  const filtered = orders.filter((o) => {
    if (filterStatus !== "ALL" && o.status !== filterStatus) return false;
    if (search) {
      const q = search.toLowerCase();
      return String(o.id).includes(q) || String(o.customer_id).includes(q) ||
        o.shipping_address?.toLowerCase().includes(q);
    }
    return true;
  });

  const totalRevenue = orders.filter((o) => o.status !== "CANCELLED" && o.status !== "REFUNDED")
    .reduce((s, o) => s + Number(o.total_amount), 0);

  if (!isAuthenticated || !isAdmin) {
    return (<><Navbar /><div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
      <ClipboardList size={40} className="text-gray-300 mb-4" />
      <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Admin Access Required</h1>
      <p className="text-gray-500 text-sm">Only admins can manage orders.</p>
    </div></>);
  }

  return (
    <><Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 animate-fade-up">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">Order Management</h1>
              <p className="text-sm text-gray-500 mt-1">{orders.length} orders · ${totalRevenue.toFixed(2)} revenue</p>
            </div>
            <button onClick={fetchOrders} disabled={loading}
              className="p-2.5 rounded-xl border border-gray-200 bg-white text-gray-500 hover:text-gray-900 hover:border-gray-300 transition-colors disabled:opacity-50">
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <div className="flex items-center bg-white border border-gray-200 rounded-full px-4 py-2 gap-2 flex-1 max-w-xs">
              <Search size={14} className="text-gray-400" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search order ID, customer..."
                className="bg-transparent text-sm outline-none flex-1 text-gray-900 placeholder-gray-400" />
            </div>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
              className="px-4 py-2 rounded-full border border-gray-200 bg-white text-sm text-gray-700 outline-none">
              <option value="ALL">All Status</option>
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {error && <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700"><AlertCircle size={16} />{error}</div>}

          {loading && orders.length === 0 ? (
            <div className="flex justify-center py-20"><Loader2 size={28} className="animate-spin text-gray-400" /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-20 text-gray-400"><Package size={28} className="mx-auto mb-2 opacity-50" /><p className="text-sm">No orders found.</p></div>
          ) : (
            <div className="space-y-3">
              {filtered.map((order) => {
                const isExp = expanded === order.id;
                const date = new Date(order.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
                const itemCount = order.items?.reduce((s, i) => s + i.quantity, 0) || 0;
                return (
                  <div key={order.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <button onClick={() => setExpanded(isExp ? null : order.id)} className="w-full flex items-center gap-4 px-5 py-4 text-left">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-sm font-semibold text-gray-900">#{order.id}</span>
                          <Badge status={order.status} />
                          <span className="text-xs text-gray-400">Customer #{order.customer_id}</span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{date} · {itemCount} items</p>
                      </div>
                      <span className="font-semibold text-gray-900 mr-2">${Number(order.total_amount).toFixed(2)}</span>
                      {isExp ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                    </button>

                    {isExp && (
                      <div className="border-t border-gray-100 px-5 py-4 space-y-4">
                        <div>
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Items</p>
                          {order.items?.map((item) => (
                            <div key={item.id} className="flex justify-between text-sm py-1">
                              <span className="text-gray-700">{item.book_title} × {item.quantity}</span>
                              <span className="font-medium">${Number(item.subtotal).toFixed(2)}</span>
                            </div>
                          ))}
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-gray-100">
                          <div><p className="text-xs text-gray-500 flex items-center gap-1"><MapPin size={11} />Address</p><p className="text-sm text-gray-700 mt-0.5">{order.shipping_address}</p></div>
                          <div><p className="text-xs text-gray-500 flex items-center gap-1"><CreditCard size={11} />Payment</p><p className="text-sm text-gray-700 mt-0.5">{order.payment_method}</p></div>
                        </div>
                        <div className="flex items-center gap-3 pt-3 border-t border-gray-100">
                          <span className="text-sm text-gray-600">Update status:</span>
                          <select value={order.status} onChange={(e) => handleStatusChange(order.id, e.target.value)}
                            className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm outline-none bg-white">
                            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                          </select>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
