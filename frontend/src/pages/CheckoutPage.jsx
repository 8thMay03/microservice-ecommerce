import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BookMarked, ArrowLeft, CreditCard, Truck, ShieldCheck,
  Loader2, AlertCircle, CheckCircle2, MapPin,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../context/CartContext";
import { ordersApi } from "../api/orders";

const PAYMENT_METHODS = [
  { id: "CREDIT_CARD", label: "Credit Card", icon: CreditCard },
  { id: "COD", label: "Cash on Delivery", icon: Truck },
];

export default function CheckoutPage() {
  const { user, token, isAuthenticated } = useAuth();
  const { items, totalPrice, clearCart } = useCart();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    fullName: user ? `${user.first_name || ""} ${user.last_name || ""}`.trim() : "",
    phone: user?.phone || "",
    address: user?.address || "",
    city: "",
    notes: "",
    paymentMethod: "CREDIT_CARD",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [orderResult, setOrderResult] = useState(null);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-stone-50 px-4">
        <BookMarked size={40} className="text-gray-300 mb-4" />
        <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Sign in to checkout</h1>
        <p className="text-gray-500 text-sm mb-6">You need an account to place orders.</p>
        <Link to="/login" state={{ from: { pathname: "/checkout" } }} className="btn-primary">
          Sign in
        </Link>
      </div>
    );
  }

  if (items.length === 0 && !orderResult) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-stone-50 px-4">
        <BookMarked size={40} className="text-gray-300 mb-4" />
        <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Cart is empty</h1>
        <p className="text-gray-500 text-sm mb-6">Add some products before checking out.</p>
        <Link to="/category/all" className="btn-primary">Browse products</Link>
      </div>
    );
  }

  if (orderResult) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-stone-50 px-4">
        <div className="bg-white rounded-2xl border border-gray-200 p-10 max-w-md w-full text-center shadow-sm">
          <CheckCircle2 size={56} className="text-green-500 mx-auto mb-5" />
          <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Order Placed!</h1>
          <p className="text-gray-500 text-sm mb-1">
            Order <span className="font-semibold text-gray-900">#{orderResult.id}</span>
          </p>
          <p className="text-gray-500 text-sm mb-6">
            Status: <span className="font-medium text-green-700">{orderResult.status}</span>
          </p>

          <div className="border-t border-gray-100 pt-5 mt-2 space-y-2">
            {orderResult.items?.map((item) => (
              <div key={item.id} className="flex justify-between text-sm">
                <span className="text-gray-600 truncate flex-1 mr-4">{item.product_title} x{item.quantity}</span>
                <span className="font-medium text-gray-900 shrink-0">${Number(item.subtotal).toFixed(2)}</span>
              </div>
            ))}
            <div className="flex justify-between text-sm font-semibold border-t border-gray-100 pt-3 mt-3">
              <span>Total</span>
              <span>${Number(orderResult.total_amount).toFixed(2)}</span>
            </div>
          </div>

          <div className="flex gap-3 mt-8">
            <Link to="/orders" className="btn-outline flex-1 py-3">My Orders</Link>
            <Link to="/category/all" className="btn-primary flex-1 py-3">Continue Shopping</Link>
          </div>
        </div>
      </div>
    );
  }

  const validate = () => {
    const errs = {};
    if (!form.fullName.trim()) errs.fullName = "Full name is required.";
    if (!form.phone.trim()) errs.phone = "Phone number is required.";
    if (!form.address.trim()) errs.address = "Address is required.";
    return errs;
  };

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (fieldErrors[field]) setFieldErrors((f) => ({ ...f, [field]: "" }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    setSubmitting(true);
    setError(null);

    try {
      const customerId = user.id;
      const shippingAddress = [form.fullName, form.phone, form.address, form.city, form.notes]
        .filter(Boolean).join(", ");

      const order = await ordersApi.create({
        customer_id: customerId,
        shipping_address: shippingAddress,
        payment_method: form.paymentMethod,
        items: items.map((item) => ({
          product_id: item.id,
          quantity: item.qty,
          unit_price: item.price,
          product_title: item.title || "",
        })),
      }, token);

      clearCart();
      setOrderResult(order);
    } catch (err) {
      setError(err.message || "Failed to place order. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors">
              <ArrowLeft size={18} />
            </Link>
            <Link to="/" className="flex items-center gap-2 text-gray-900">
              <BookMarked size={22} strokeWidth={1.8} />
              <span className="font-serif text-lg">Checkout</span>
            </Link>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <ShieldCheck size={14} />
            Secure checkout
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 animate-fade-up">
        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: form */}
          <div className="lg:col-span-7">
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Shipping info */}
              <section className="bg-white rounded-2xl border border-gray-200 p-6">
                <h2 className="font-serif text-xl font-medium text-gray-900 mb-5 flex items-center gap-2">
                  <MapPin size={18} />
                  Shipping Information
                </h2>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                      <input
                        type="text" value={form.fullName} onChange={set("fullName")}
                        className={`w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors ${
                          fieldErrors.fullName ? "border-red-300 ring-1 ring-red-200" : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"}`}
                      />
                      {fieldErrors.fullName && <p className="text-xs text-red-500 mt-1">{fieldErrors.fullName}</p>}
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
                      <input
                        type="tel" value={form.phone} onChange={set("phone")}
                        className={`w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors ${
                          fieldErrors.phone ? "border-red-300 ring-1 ring-red-200" : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"}`}
                      />
                      {fieldErrors.phone && <p className="text-xs text-red-500 mt-1">{fieldErrors.phone}</p>}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Address *</label>
                    <input
                      type="text" value={form.address} onChange={set("address")}
                      placeholder="Street, apartment, etc."
                      className={`w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors ${
                        fieldErrors.address ? "border-red-300 ring-1 ring-red-200" : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"}`}
                    />
                    {fieldErrors.address && <p className="text-xs text-red-500 mt-1">{fieldErrors.address}</p>}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                      <input
                        type="text" value={form.city} onChange={set("city")}
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm bg-white outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                      <input
                        type="text" value={form.notes} onChange={set("notes")}
                        placeholder="Delivery instructions (optional)"
                        className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm bg-white outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
                      />
                    </div>
                  </div>
                </div>
              </section>

              {/* Payment method */}
              <section className="bg-white rounded-2xl border border-gray-200 p-6">
                <h2 className="font-serif text-xl font-medium text-gray-900 mb-5 flex items-center gap-2">
                  <CreditCard size={18} />
                  Payment Method
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {PAYMENT_METHODS.map((m) => {
                    const Icon = m.icon;
                    const active = form.paymentMethod === m.id;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setForm((f) => ({ ...f, paymentMethod: m.id }))}
                        className={`flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all ${
                          active
                            ? "border-gray-900 bg-gray-50"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          active ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-500"
                        }`}>
                          <Icon size={18} />
                        </div>
                        <span className={`text-sm font-medium ${active ? "text-gray-900" : "text-gray-600"}`}>
                          {m.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* Submit (mobile) */}
              <div className="lg:hidden">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-4 rounded-xl text-sm font-medium hover:bg-gray-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                >
                  {submitting ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                  {submitting ? "Placing order…" : `Pay $${totalPrice.toFixed(2)}`}
                </button>
              </div>
            </form>
          </div>

          {/* Right: order summary */}
          <div className="lg:col-span-5">
            <div className="bg-white rounded-2xl border border-gray-200 p-6 lg:sticky lg:top-24">
              <h2 className="font-serif text-xl font-medium text-gray-900 mb-5">Order Summary</h2>

              <ul className="space-y-4 mb-6">
                {items.map((item) => (
                  <li key={item.id} className="flex gap-4">
                    <img
                      src={item.image}
                      alt={item.title}
                      className="w-14 h-[72px] object-cover rounded-sm bg-gray-100 shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 line-clamp-2">{item.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">Qty: {item.qty}</p>
                    </div>
                    <span className="text-sm font-semibold text-gray-900 shrink-0">
                      ${(item.price * item.qty).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="space-y-2 border-t border-gray-100 pt-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Subtotal</span>
                  <span className="text-gray-900">${totalPrice.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Shipping</span>
                  <span className="text-green-600 font-medium">Free</span>
                </div>
                <div className="flex justify-between font-semibold text-lg border-t border-gray-100 pt-3 mt-3">
                  <span>Total</span>
                  <span>${totalPrice.toFixed(2)}</span>
                </div>
              </div>

              {/* Submit (desktop) */}
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="hidden lg:flex w-full items-center justify-center gap-2 bg-gray-900 text-white py-4 rounded-xl text-sm font-medium hover:bg-gray-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors mt-6"
              >
                {submitting ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                {submitting ? "Placing order…" : `Place Order — $${totalPrice.toFixed(2)}`}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
