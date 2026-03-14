import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Eye, EyeOff, BookMarked, ArrowRight, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const DECORATIVE_BOOKS = [
  { title: "Letters from M/M (Paris)", author: "M/M Paris", color: "bg-amber-100" },
  { title: "Dieter Rams: Complete Works", author: "Klaus Klemp", color: "bg-slate-200" },
  { title: "Album Architectures", author: "Luís Loureiro", color: "bg-stone-300" },
];

export default function LoginPage() {
  const { login, loading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/";

  const [form, setForm] = useState({ email: "", password: "" });
  const [showPw, setShowPw] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) navigate(from, { replace: true });
  }, [isAuthenticated, navigate, from]);

  useEffect(() => {
    clearError();
  }, []);

  const validate = () => {
    const errs = {};
    if (!form.email) errs.email = "Email is required.";
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = "Enter a valid email.";
    if (!form.password) errs.password = "Password is required.";
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});

    const result = await login(form.email, form.password);
    if (result.ok) navigate(from, { replace: true });
  };

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (fieldErrors[field]) setFieldErrors((f) => ({ ...f, [field]: "" }));
  };

  return (
    <div className="min-h-screen flex animate-fade-up">
      {/* ── Left panel (decorative) ─────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-gray-950 flex-col justify-between p-12 relative overflow-hidden">
        {/* Background texture */}
        <div className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-white relative z-10">
          <BookMarked size={22} strokeWidth={1.8} />
          <span className="font-serif text-lg">Bookstore</span>
        </Link>

        {/* Center copy */}
        <div className="relative z-10">
          <p className="text-xs tracking-[0.25em] uppercase text-gray-500 mb-5">
            Welcome back
          </p>
          <h2 className="font-serif text-4xl xl:text-5xl text-white font-medium leading-tight">
            Your next great<br />
            <em className="not-italic text-gray-400">read awaits.</em>
          </h2>
          <p className="mt-5 text-gray-500 text-sm leading-relaxed max-w-xs">
            Sign in to access your cart, order history, and personalised
            recommendations.
          </p>

          {/* Decorative book stack */}
          <div className="mt-10 flex gap-3">
            {DECORATIVE_BOOKS.map((b, i) => (
              <div
                key={i}
                className={`${b.color} rounded-sm p-3 flex flex-col justify-end`}
                style={{ width: 72, height: 96 }}
              >
                <p className="text-[9px] font-semibold text-gray-700 leading-tight line-clamp-2">
                  {b.title}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer quote */}
        <p className="text-gray-600 text-xs relative z-10">
          "A reader lives a thousand lives before he dies."
          <span className="block mt-1 text-gray-700">— George R.R. Martin</span>
        </p>
      </div>

      {/* ── Right panel (form) ──────────────────────────────────────── */}
      <div className="flex-1 flex flex-col justify-center items-center px-6 py-12 bg-stone-50">
        {/* Mobile logo */}
        <div className="lg:hidden mb-10">
          <Link to="/" className="flex items-center gap-2 text-gray-900">
            <BookMarked size={22} strokeWidth={1.8} />
            <span className="font-serif text-lg">Bookstore</span>
          </Link>
        </div>

        <div className="w-full max-w-sm">
          {/* Heading */}
          <div className="mb-8">
            <h1 className="font-serif text-3xl font-medium text-gray-900">
              Sign in
            </h1>
            <p className="text-gray-500 text-sm mt-2">
              New here?{" "}
              <Link
                to="/register"
                className="text-gray-900 font-medium underline underline-offset-2 hover:text-gray-600 transition-colors"
              >
                Create an account
              </Link>
            </p>
          </div>

          {/* API-level error */}
          {error && (
            <div className="flex items-start gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={set("email")}
                placeholder="you@example.com"
                className={`w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors
                  ${fieldErrors.email
                    ? "border-red-300 focus:border-red-400 ring-1 ring-red-200"
                    : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
                  }`}
              />
              {fieldErrors.email && (
                <p className="text-xs text-red-500 mt-1.5">{fieldErrors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-gray-700">
                  Password
                </label>
                <button
                  type="button"
                  className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  autoComplete="current-password"
                  value={form.password}
                  onChange={set("password")}
                  placeholder="••••••••"
                  className={`w-full px-4 py-3 pr-11 rounded-xl border text-sm bg-white outline-none transition-colors
                    ${fieldErrors.password
                      ? "border-red-300 focus:border-red-400 ring-1 ring-red-200"
                      : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
                    }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {fieldErrors.password && (
                <p className="text-xs text-red-500 mt-1.5">{fieldErrors.password}</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3.5 rounded-xl text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-7">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-stone-50 px-3 text-xs text-gray-400">
                or continue as guest
              </span>
            </div>
          </div>

          <Link
            to="/"
            className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-700 py-3 rounded-xl text-sm font-medium hover:border-gray-400 hover:text-gray-900 transition-colors"
          >
            Browse without account
          </Link>
        </div>
      </div>
    </div>
  );
}
