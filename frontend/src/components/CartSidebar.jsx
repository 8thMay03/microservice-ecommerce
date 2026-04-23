import { X, Minus, Plus, Trash2, ShoppingBag, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useCart } from "../context/CartContext";

export default function CartSidebar() {
  const { items, isOpen, setIsOpen, increment, decrement, removeFromCart, totalItems, totalPrice, toast } =
    useCart();

  return (
    <>
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[60] animate-fade-in-down">
          <div className="flex items-center gap-2 bg-gray-900 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium">
            <CheckCircle2 size={16} className="text-green-400 shrink-0" />
            {toast}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Drawer */}
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-full sm:w-96 bg-white shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <ShoppingBag size={18} />
            <h2 className="font-serif text-lg font-semibold">
              Cart
              {totalItems > 0 && (
                <span className="ml-2 text-sm font-sans font-normal text-gray-500">
                  ({totalItems} item{totalItems > 1 ? "s" : ""})
                </span>
              )}
            </h2>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 rounded-full hover:bg-gray-100 text-gray-500 hover:text-gray-900 transition-colors"
            aria-label="Close cart"
          >
            <X size={18} />
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                <ShoppingBag size={24} className="text-gray-400" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Your cart is empty</p>
                <p className="text-sm text-gray-500 mt-1">
                  Discover products you'll love.
                </p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="btn-primary mt-2"
              >
                Browse products
              </button>
            </div>
          ) : (
            <ul className="space-y-5">
              {items.map((item) => (
                <li key={item.id} className="flex gap-4">
                  <Link
                    to={`/product/${item.id}`}
                    onClick={() => setIsOpen(false)}
                    className="shrink-0"
                  >
                    <img
                      src={item.image}
                      alt={item.title}
                      className="w-16 h-20 object-cover rounded-sm bg-gray-100"
                    />
                  </Link>

                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/product/${item.id}`}
                      onClick={() => setIsOpen(false)}
                      className="text-sm font-medium text-gray-900 line-clamp-2 hover:text-gray-600 transition-colors"
                    >
                      {item.title}
                    </Link>
                    <p className="text-xs text-gray-500 mt-0.5">{item.brand || item.author}</p>

                    <div className="flex items-center justify-between mt-3">
                      {/* Qty controls */}
                      <div className="flex items-center border border-gray-200 rounded-full overflow-hidden">
                        <button
                          onClick={() => decrement(item.id)}
                          className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 transition-colors"
                        >
                          <Minus size={12} />
                        </button>
                        <span className="px-2 text-sm font-medium w-7 text-center">
                          {item.qty}
                        </span>
                        <button
                          onClick={() => increment(item.id)}
                          className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 transition-colors"
                        >
                          <Plus size={12} />
                        </button>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-sm font-semibold text-gray-900">
                          ${(item.price * item.qty).toFixed(2)}
                        </span>
                        <button
                          onClick={() => removeFromCart(item.id)}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                          aria-label={`Remove ${item.title}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="px-6 py-5 border-t border-gray-100 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Subtotal</span>
              <span className="font-serif text-lg font-semibold">
                ${totalPrice.toFixed(2)}
              </span>
            </div>
            <p className="text-xs text-gray-400">
              Shipping and taxes calculated at checkout.
            </p>
            <Link
              to="/checkout"
              onClick={() => setIsOpen(false)}
              className="btn-primary w-full py-3 text-center rounded-full block"
            >
              Checkout → ${totalPrice.toFixed(2)}
            </Link>
            <button
              onClick={() => setIsOpen(false)}
              className="btn-outline w-full py-3 text-center"
            >
              Continue shopping
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
