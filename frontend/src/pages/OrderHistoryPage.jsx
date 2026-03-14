import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Package, Clock, CheckCircle2, XCircle, Truck, CreditCard,
  AlertCircle, Loader2, BookMarked, ChevronDown, ChevronUp,
  RefreshCw, MapPin,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { ordersApi } from "../api/orders";

const STATUS_CONFIG = {
  PENDING:   { label: "Pending",   color: "bg-yellow-100 text-yellow-800", icon: Clock },
  CONFIRMED: { label: "Confirmed", color: "bg-blue-100 text-blue-800",     icon: CheckCircle2 },
  PAID:      { label: "Paid",      color: "bg-emerald-100 text-emerald-800", icon: CreditCard },
  SHIPPED:   { label: "Shipped",   color: "bg-indigo-100 text-indigo-800", icon: Truck },
  DELIVERED: { label: "Delivered", color: "bg-green-100 text-green-800",   icon: CheckCircle2 },
  CANCELLED: { label: "Cancelled", color: "bg-red-100 text-red-800",       icon: XCircle },
  REFUNDED:  { label: "Refunded",  color: "bg-gray-100 text-gray-800",     icon: RefreshCw },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.color}`}>
      <Icon size={12} />
      {cfg.label}
    </span>
  );
}

function OrderCard({ order }) {
  const [expanded, setExpanded] = useState(false);
  const date = new Date(order.created_at).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
  const itemCount = order.items?.reduce((sum, i) => sum + i.quantity, 0) || 0;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden transition-shadow hover:shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-4 px-5 py-4 sm:px-6 sm:py-5 text-left"
      >
        <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center shrink-0">
          <Package size={18} className="text-gray-500" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-semibold text-gray-900">Order #{order.id}</span>
            <StatusBadge status={order.status} />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {date} · {itemCount} item{itemCount !== 1 ? "s" : ""}
          </p>
        </div>

        <span className="font-serif text-lg font-semibold text-gray-900 shrink-0 mr-2">
          ${Number(order.total_amount).toFixed(2)}
        </span>

        {expanded ? (
          <ChevronUp size={16} className="text-gray-400 shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-gray-400 shrink-0" />
        )}
      </button>

      {/* Detail */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 sm:px-6 sm:py-5 space-y-4">
          {/* Items */}
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Items</h4>
            <ul className="space-y-3">
              {order.items?.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center shrink-0">
                      <BookMarked size={14} className="text-gray-400" />
                    </div>
                    <div className="min-w-0">
                      <Link
                        to={`/book/${item.book_id}`}
                        className="text-sm font-medium text-gray-900 hover:text-gray-600 transition-colors line-clamp-1"
                      >
                        {item.book_title || `Book #${item.book_id}`}
                      </Link>
                      <p className="text-xs text-gray-500">
                        ${Number(item.unit_price).toFixed(2)} × {item.quantity}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm font-semibold text-gray-900 shrink-0">
                    ${Number(item.subtotal).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Shipping & Payment */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-gray-100">
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                <MapPin size={11} /> Shipping Address
              </h4>
              <p className="text-sm text-gray-700">{order.shipping_address}</p>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                <CreditCard size={11} /> Payment
              </h4>
              <p className="text-sm text-gray-700">
                {order.payment_method === "CREDIT_CARD" ? "Credit Card" :
                 order.payment_method === "COD" ? "Cash on Delivery" :
                 order.payment_method}
              </p>
            </div>
          </div>

          {/* Summary */}
          <div className="flex justify-between items-center pt-3 border-t border-gray-100">
            <span className="text-sm text-gray-500">Total</span>
            <span className="font-serif text-lg font-semibold text-gray-900">
              ${Number(order.total_amount).toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function OrderHistoryPage() {
  const { user, token, isAuthenticated } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOrders = useCallback(async () => {
    if (!user?.id || !token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await ordersApi.list(user.id, token);
      const list = Array.isArray(data) ? data : data.results ?? [];
      setOrders(list);
    } catch (err) {
      setError(err.message || "Failed to load orders.");
    } finally {
      setLoading(false);
    }
  }, [user?.id, token]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  if (!isAuthenticated) {
    return (
      <>
        <Navbar />
        <div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
          <Package size={40} className="text-gray-300 mb-4" />
          <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Sign in to view orders</h1>
          <p className="text-gray-500 text-sm mb-6">You need an account to see your order history.</p>
          <Link to="/login" state={{ from: { pathname: "/orders" } }} className="btn-primary">
            Sign in
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12 animate-fade-up">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">Order History</h1>
              <p className="text-sm text-gray-500 mt-1">
                {orders.length > 0
                  ? `${orders.length} order${orders.length !== 1 ? "s" : ""}`
                  : "Track your past purchases"}
              </p>
            </div>
            <button
              onClick={fetchOrders}
              disabled={loading}
              className="p-2.5 rounded-xl border border-gray-200 bg-white text-gray-500 hover:text-gray-900 hover:border-gray-300 transition-colors disabled:opacity-50"
              aria-label="Refresh"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Loading */}
          {loading && orders.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
              <Loader2 size={28} className="animate-spin mb-3" />
              <span className="text-sm">Loading orders…</span>
            </div>
          )}

          {/* Empty */}
          {!loading && !error && orders.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <Package size={24} className="text-gray-400" />
              </div>
              <h2 className="font-medium text-gray-900 mb-1">No orders yet</h2>
              <p className="text-sm text-gray-500 mb-6">When you place an order, it will appear here.</p>
              <Link to="/category/all" className="btn-primary">Browse books</Link>
            </div>
          )}

          {/* Orders */}
          {orders.length > 0 && (
            <div className="space-y-4">
              {orders.map((order) => (
                <OrderCard key={order.id} order={order} />
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
