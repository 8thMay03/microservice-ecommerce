import { useState, useEffect, useCallback, useMemo } from "react";
import {
  DollarSign, Loader2, AlertCircle, RefreshCw,
  TrendingUp, ShoppingBag, Package, BarChart3,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { adminOrdersApi } from "../api/admin";

export default function AdminRevenuePage() {
  const { user, token, isAuthenticated } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  const stats = useMemo(() => {
    const paid = orders.filter((o) => !["CANCELLED", "REFUNDED"].includes(o.status));
    const cancelled = orders.filter((o) => o.status === "CANCELLED");
    const totalRevenue = paid.reduce((s, o) => s + Number(o.total_amount), 0);
    const totalItems = paid.reduce((s, o) => s + (o.items?.reduce((a, i) => a + i.quantity, 0) || 0), 0);

    const byMonth = {};
    paid.forEach((o) => {
      const d = new Date(o.created_at);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      if (!byMonth[key]) byMonth[key] = { revenue: 0, orders: 0 };
      byMonth[key].revenue += Number(o.total_amount);
      byMonth[key].orders += 1;
    });

    const byStatus = {};
    orders.forEach((o) => {
      byStatus[o.status] = (byStatus[o.status] || 0) + 1;
    });

    const topBooks = {};
    paid.forEach((o) => o.items?.forEach((i) => {
      const key = i.book_title || `Book #${i.book_id}`;
      if (!topBooks[key]) topBooks[key] = { title: key, qty: 0, revenue: 0 };
      topBooks[key].qty += i.quantity;
      topBooks[key].revenue += Number(i.subtotal);
    }));
    const topBooksList = Object.values(topBooks).sort((a, b) => b.revenue - a.revenue).slice(0, 10);

    const monthlyList = Object.entries(byMonth).sort(([a], [b]) => b.localeCompare(a));

    return { totalRevenue, totalOrders: paid.length, cancelledOrders: cancelled.length, totalItems, monthlyList, byStatus, topBooksList };
  }, [orders]);

  if (!isAuthenticated || !isAdmin) {
    return (<><Navbar /><div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
      <DollarSign size={40} className="text-gray-300 mb-4" /><h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Admin Access Required</h1></div></>);
  }

  return (
    <><Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 animate-fade-up">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">Revenue Dashboard</h1>
              <p className="text-sm text-gray-500 mt-1">Overview of sales performance</p>
            </div>
            <button onClick={fetchOrders} disabled={loading}
              className="p-2.5 rounded-xl border border-gray-200 bg-white text-gray-500 hover:text-gray-900 transition-colors disabled:opacity-50">
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>

          {error && <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700"><AlertCircle size={16} />{error}</div>}

          {loading ? (
            <div className="flex justify-center py-20"><Loader2 size={28} className="animate-spin text-gray-400" /></div>
          ) : (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-fade-up animate-delay-1">
                {[
                  { label: "Total Revenue", value: `$${stats.totalRevenue.toFixed(2)}`, icon: DollarSign, color: "text-green-600 bg-green-50" },
                  { label: "Orders", value: stats.totalOrders, icon: Package, color: "text-blue-600 bg-blue-50" },
                  { label: "Items Sold", value: stats.totalItems, icon: ShoppingBag, color: "text-purple-600 bg-purple-50" },
                  { label: "Cancelled", value: stats.cancelledOrders, icon: TrendingUp, color: "text-red-600 bg-red-50" },
                ].map((c) => (
                  <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-3 mb-3">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${c.color}`}><c.icon size={18} /></div>
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{c.label}</span>
                    </div>
                    <p className="font-serif text-2xl font-semibold text-gray-900">{c.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Monthly breakdown */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 animate-fade-up animate-delay-2">
                  <h2 className="font-serif text-lg font-medium text-gray-900 mb-4 flex items-center gap-2"><BarChart3 size={18} />Monthly Revenue</h2>
                  {stats.monthlyList.length === 0 ? (
                    <p className="text-sm text-gray-400 py-4 text-center">No data yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {stats.monthlyList.map(([month, d]) => {
                        const pct = stats.totalRevenue > 0 ? (d.revenue / stats.totalRevenue) * 100 : 0;
                        return (
                          <div key={month}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-gray-700 font-medium">{month}</span>
                              <span className="text-gray-900 font-semibold">${d.revenue.toFixed(2)} <span className="text-gray-400 font-normal">({d.orders} orders)</span></span>
                            </div>
                            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div className="h-full bg-gray-900 rounded-full transition-all" style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Top selling books */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 animate-fade-up animate-delay-3">
                  <h2 className="font-serif text-lg font-medium text-gray-900 mb-4 flex items-center gap-2"><TrendingUp size={18} />Top Selling Books</h2>
                  {stats.topBooksList.length === 0 ? (
                    <p className="text-sm text-gray-400 py-4 text-center">No sales yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {stats.topBooksList.map((b, i) => (
                        <div key={b.title} className="flex items-center gap-3">
                          <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-500 text-xs font-semibold flex items-center justify-center shrink-0">{i + 1}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{b.title}</p>
                            <p className="text-xs text-gray-500">{b.qty} sold</p>
                          </div>
                          <span className="text-sm font-semibold text-gray-900">${b.revenue.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Status distribution */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 animate-fade-up animate-delay-4 lg:col-span-2">
                  <h2 className="font-serif text-lg font-medium text-gray-900 mb-4">Order Status Distribution</h2>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(stats.byStatus).map(([status, count]) => (
                      <div key={status} className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-xl">
                        <span className="text-sm font-medium text-gray-700">{status}</span>
                        <span className="px-2 py-0.5 bg-gray-900 text-white text-xs font-semibold rounded-full">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}
