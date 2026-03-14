import { createContext, useContext, useState, useCallback } from "react";
import { authApi } from "../api/auth";

const AuthContext = createContext(null);

const TOKEN_KEY = "bs_access_token";
const USER_KEY = "bs_user";

function loadFromStorage() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = JSON.parse(localStorage.getItem(USER_KEY) || "null");
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
}

export function AuthProvider({ children }) {
  const [{ token, user }, setAuth] = useState(loadFromStorage);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const _persist = (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    setAuth({ token, user });
  };

  const clearError = () => setError(null);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      // Try customer first
      const data = await authApi.login(email, password);
      _persist(data.tokens.access, { ...data.customer, role: "customer" });
      return { ok: true };
    } catch {
      // Try manager
      try {
        const data = await authApi.loginManager(email, password);
        _persist(data.tokens.access, { ...data.manager, role: "manager" });
        return { ok: true };
      } catch {
        // Try staff
        try {
          const data = await authApi.loginStaff(email, password);
          _persist(data.tokens.access, { ...data.staff, role: "staff" });
          return { ok: true };
        } catch (err) {
          const msg = err.message || "Invalid email or password.";
          setError(msg);
          return { ok: false, error: msg };
        }
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const data = await authApi.register(payload);
      _persist(data.tokens.access, { ...data.customer, role: "customer" });
      return { ok: true };
    } catch (err) {
      const msg = err.message || "Registration failed. Please try again.";
      setError(msg);
      return { ok: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUser = useCallback((updatedFields) => {
    setAuth((prev) => {
      const merged = { ...prev.user, ...updatedFields };
      localStorage.setItem(USER_KEY, JSON.stringify(merged));
      return { ...prev, user: merged };
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setAuth({ token: null, user: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        loading,
        error,
        clearError,
        login,
        register,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};
