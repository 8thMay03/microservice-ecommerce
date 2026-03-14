import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Eye, EyeOff, BookMarked, ArrowRight,
  AlertCircle, Loader2, Check,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

/* Password strength helpers */
const STRENGTH_RULES = [
  { label: "At least 8 characters", test: (p) => p.length >= 8 },
  { label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "One number", test: (p) => /\d/.test(p) },
];

function PasswordStrength({ password }) {
  if (!password) return null;
  const passed = STRENGTH_RULES.filter((r) => r.test(password)).length;
  const colors = ["bg-red-400", "bg-amber-400", "bg-green-500"];
  const labels = ["Weak", "Fair", "Strong"];
  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
              i < passed ? colors[passed - 1] : "bg-gray-200"
            }`}
          />
        ))}
      </div>
      <p className={`text-xs font-medium ${passed === 3 ? "text-green-600" : passed === 2 ? "text-amber-600" : "text-red-500"}`}>
        {labels[passed - 1] ?? "Too weak"}
      </p>
      <ul className="space-y-0.5">
        {STRENGTH_RULES.map((r) => (
          <li key={r.label} className={`flex items-center gap-1.5 text-xs transition-colors ${r.test(password) ? "text-green-600" : "text-gray-400"}`}>
            <Check size={10} className={r.test(password) ? "opacity-100" : "opacity-0"} />
            {r.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* Single reusable field component */
function Field({ label, error, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
      {hint && !error && <p className="text-xs text-gray-400 mt-1.5">{hint}</p>}
      {error && <p className="text-xs text-red-500 mt-1.5">{error}</p>}
    </div>
  );
}

function Input({ error, ...props }) {
  return (
    <input
      {...props}
      className={`w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors
        ${error
          ? "border-red-300 focus:border-red-400 ring-1 ring-red-200"
          : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
        } ${props.className ?? ""}`}
    />
  );
}

const STEPS = ["Account", "Personal", "Done"];

export default function RegisterPage() {
  const { register, loading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const [form, setForm] = useState({
    email: "",
    password: "",
    password_confirm: "",
    first_name: "",
    last_name: "",
    phone: "",
    address: "",
  });

  useEffect(() => { if (isAuthenticated) navigate("/", { replace: true }); }, [isAuthenticated]);
  useEffect(() => { clearError(); }, []);

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (fieldErrors[field]) setFieldErrors((f) => ({ ...f, [field]: "" }));
  };

  /* Step-level validation */
  const validateStep = (s) => {
    const errs = {};
    if (s === 0) {
      if (!form.email) errs.email = "Email is required.";
      else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = "Enter a valid email.";
      if (!form.password) errs.password = "Password is required.";
      else if (form.password.length < 8) errs.password = "Minimum 8 characters.";
      if (!form.password_confirm) errs.password_confirm = "Please confirm your password.";
      else if (form.password !== form.password_confirm) errs.password_confirm = "Passwords do not match.";
    }
    if (s === 1) {
      if (!form.first_name.trim()) errs.first_name = "First name is required.";
      if (!form.last_name.trim()) errs.last_name = "Last name is required.";
    }
    return errs;
  };

  const nextStep = () => {
    const errs = validateStep(step);
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    setStep((s) => s + 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validateStep(step);
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    await register(form);
  };

  return (
    <div className="min-h-screen flex animate-fade-up">
      {/* ── Left panel ────────────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-1/2 bg-gray-950 flex-col justify-between p-12 relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />

        <Link to="/" className="flex items-center gap-2 text-white relative z-10">
          <BookMarked size={22} strokeWidth={1.8} />
          <span className="font-serif text-lg">Bookstore</span>
        </Link>

        <div className="relative z-10">
          <p className="text-xs tracking-[0.25em] uppercase text-gray-500 mb-5">
            New account
          </p>
          <h2 className="font-serif text-4xl xl:text-5xl text-white font-medium leading-tight">
            Join a community<br />
            <em className="not-italic text-gray-400">of readers.</em>
          </h2>
          <p className="mt-5 text-gray-500 text-sm leading-relaxed max-w-xs">
            Get personalised recommendations, track your orders, and discover
            books curated just for you.
          </p>

          {/* Feature list */}
          <ul className="mt-10 space-y-3">
            {[
              "Personalised book recommendations",
              "Track your orders in real time",
              "Save wishlist and return to it anytime",
              "Exclusive member-only offers",
            ].map((feat) => (
              <li key={feat} className="flex items-center gap-3 text-sm text-gray-400">
                <div className="w-5 h-5 rounded-full bg-gray-800 flex items-center justify-center shrink-0">
                  <Check size={10} className="text-gray-400" />
                </div>
                {feat}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-gray-600 text-xs relative z-10">
          "Not all those who wander are lost."
          <span className="block mt-1 text-gray-700">— J.R.R. Tolkien</span>
        </p>
      </div>

      {/* ── Right panel (multi-step form) ─────────────────────────── */}
      <div className="flex-1 flex flex-col justify-center items-center px-6 py-12 bg-stone-50">
        {/* Mobile logo */}
        <div className="lg:hidden mb-8">
          <Link to="/" className="flex items-center gap-2 text-gray-900">
            <BookMarked size={22} strokeWidth={1.8} />
            <span className="font-serif text-lg">Bookstore</span>
          </Link>
        </div>

        <div className="w-full max-w-sm">
          {/* Step progress */}
          <div className="flex items-center gap-2 mb-8">
            {STEPS.map((label, i) => (
              <div key={label} className="flex items-center gap-2">
                <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-all duration-300
                  ${i < step ? "bg-green-500 text-white"
                    : i === step ? "bg-gray-900 text-white"
                    : "bg-gray-200 text-gray-500"
                  }`}
                >
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-gray-900" : "text-gray-400"}`}>
                  {label}
                </span>
                {i < STEPS.length - 1 && (
                  <div className={`h-px w-6 sm:w-10 transition-colors duration-300 ${i < step ? "bg-green-400" : "bg-gray-200"}`} />
                )}
              </div>
            ))}
          </div>

          {/* Heading */}
          <div className="mb-7">
            <h1 className="font-serif text-3xl font-medium text-gray-900">
              {step === 0 ? "Create account" : step === 1 ? "Your details" : "All set!"}
            </h1>
            <p className="text-gray-500 text-sm mt-2">
              {step === 0
                ? <>Already have one?{" "}<Link to="/login" className="text-gray-900 font-medium underline underline-offset-2 hover:text-gray-600 transition-colors">Sign in</Link></>
                : step === 1
                ? "Tell us a bit about yourself."
                : "Your account has been created."}
            </p>
          </div>

          {/* API-level error */}
          {error && (
            <div className="flex items-start gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* ── Step 0: Account credentials ── */}
          {step === 0 && (
            <div className="space-y-5">
              <Field label="Email address" error={fieldErrors.email}>
                <Input
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={set("email")}
                  placeholder="you@example.com"
                  error={fieldErrors.email}
                />
              </Field>

              <Field label="Password" error={fieldErrors.password}>
                <div className="relative">
                  <Input
                    type={showPw ? "text" : "password"}
                    autoComplete="new-password"
                    value={form.password}
                    onChange={set("password")}
                    placeholder="••••••••"
                    error={fieldErrors.password}
                    className="pr-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <PasswordStrength password={form.password} />
              </Field>

              <Field label="Confirm password" error={fieldErrors.password_confirm}>
                <div className="relative">
                  <Input
                    type={showConfirm ? "text" : "password"}
                    autoComplete="new-password"
                    value={form.password_confirm}
                    onChange={set("password_confirm")}
                    placeholder="••••••••"
                    error={fieldErrors.password_confirm}
                    className="pr-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((v) => !v)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </Field>

              <button
                type="button"
                onClick={nextStep}
                className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white py-3.5 rounded-xl text-sm font-medium hover:bg-gray-700 transition-colors mt-2"
              >
                Continue <ArrowRight size={15} />
              </button>
            </div>
          )}

          {/* ── Step 1: Personal details ── */}
          {step === 1 && (
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Field label="First name" error={fieldErrors.first_name}>
                  <Input
                    type="text"
                    autoComplete="given-name"
                    value={form.first_name}
                    onChange={set("first_name")}
                    placeholder="Alice"
                    error={fieldErrors.first_name}
                  />
                </Field>
                <Field label="Last name" error={fieldErrors.last_name}>
                  <Input
                    type="text"
                    autoComplete="family-name"
                    value={form.last_name}
                    onChange={set("last_name")}
                    placeholder="Smith"
                    error={fieldErrors.last_name}
                  />
                </Field>
              </div>

              <Field label="Phone" hint="Optional — for order notifications.">
                <Input
                  type="tel"
                  autoComplete="tel"
                  value={form.phone}
                  onChange={set("phone")}
                  placeholder="+1 555 000 0000"
                />
              </Field>

              <Field label="Shipping address" hint="Optional — you can add this later.">
                <textarea
                  value={form.address}
                  onChange={set("address")}
                  rows={2}
                  placeholder="123 Main St, City, Country"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200 text-sm bg-white outline-none transition-colors resize-none"
                />
              </Field>

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => { setStep(0); setFieldErrors({}); }}
                  className="flex-1 py-3 rounded-xl border border-gray-200 text-sm font-medium text-gray-700 hover:border-gray-400 hover:text-gray-900 transition-colors"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 bg-gray-900 text-white py-3 rounded-xl text-sm font-medium hover:bg-gray-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <><Loader2 size={16} className="animate-spin" /> Creating…</>
                  ) : (
                    <>Create account <ArrowRight size={15} /></>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* ── Step 2: Success (shown briefly before redirect) ── */}
          {step === 2 && (
            <div className="text-center py-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-5">
                <Check size={28} className="text-green-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-gray-900 mb-2">
                Welcome aboard!
              </h2>
              <p className="text-gray-500 text-sm mb-6">
                Your account is ready. Redirecting you to the homepage…
              </p>
              <Link to="/" className="btn-primary inline-flex">
                Browse books <ArrowRight size={14} className="ml-1.5" />
              </Link>
            </div>
          )}

          {/* Terms note */}
          {step < 2 && (
            <p className="text-center text-xs text-gray-400 mt-6 leading-relaxed">
              By creating an account you agree to our{" "}
              <a href="#" className="underline hover:text-gray-600">Terms of Service</a>{" "}
              and{" "}
              <a href="#" className="underline hover:text-gray-600">Privacy Policy</a>.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
