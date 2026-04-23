import { createContext, useContext, useReducer, useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "./AuthContext";

const CartContext = createContext(null);

const CART_STORAGE_PREFIX = "bs_cart_";

function cartReducer(state, action) {
  switch (action.type) {
    case "SET":
      return action.items ?? [];
    case "ADD": {
      const existing = state.find((i) => i.id === action.product.id);
      if (existing) {
        return state.map((i) =>
          i.id === action.product.id ? { ...i, qty: i.qty + 1 } : i
        );
      }
      return [...state, { ...action.product, qty: 1 }];
    }
    case "REMOVE":
      return state.filter((i) => i.id !== action.id);
    case "INCREMENT":
      return state.map((i) =>
        i.id === action.id ? { ...i, qty: i.qty + 1 } : i
      );
    case "DECREMENT":
      return state
        .map((i) => (i.id === action.id ? { ...i, qty: i.qty - 1 } : i))
        .filter((i) => i.qty > 0);
    case "CLEAR":
      return [];
    default:
      return state;
  }
}

function getCartKey(user) {
  if (user?.id) return `${CART_STORAGE_PREFIX}user_${user.id}`;
  return `${CART_STORAGE_PREFIX}guest`;
}

function loadCartFromStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCartToStorage(key, items) {
  try {
    localStorage.setItem(key, JSON.stringify(items));
  } catch {
    // ignore
  }
}

export function CartProvider({ children }) {
  const { user } = useAuth();
  const cartKey = getCartKey(user);

  const [items, dispatch] = useReducer(cartReducer, []);
  const [isOpen, setIsOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  // Load cart when user changes (login/logout)
  useEffect(() => {
    const saved = loadCartFromStorage(cartKey);
    dispatch({ type: "SET", items: saved });
  }, [cartKey]);

  // Save cart when items change
  useEffect(() => {
    saveCartToStorage(cartKey, items);
  }, [cartKey, items]);

  const showToast = useCallback((message) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2000);
  }, []);

  const addToCart = (product) => {
    dispatch({ type: "ADD", product });
    showToast("Đã thêm vào giỏ hàng");
  };

  const removeFromCart = (id) => dispatch({ type: "REMOVE", id });
  const increment = (id) => dispatch({ type: "INCREMENT", id });
  const decrement = (id) => dispatch({ type: "DECREMENT", id });
  const clearCart = () => dispatch({ type: "CLEAR" });

  const totalItems = items.reduce((sum, i) => sum + i.qty, 0);
  const totalPrice = items.reduce((sum, i) => sum + i.price * i.qty, 0);

  return (
    <CartContext.Provider
      value={{
        items,
        isOpen,
        setIsOpen,
        addToCart,
        removeFromCart,
        increment,
        decrement,
        clearCart,
        totalItems,
        totalPrice,
        toast,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used inside CartProvider");
  return ctx;
};
