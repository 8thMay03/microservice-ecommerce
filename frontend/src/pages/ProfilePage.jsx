import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  User, Mail, Phone, MapPin, Save, Loader2,
  AlertCircle, CheckCircle2, BookMarked,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { profileApi } from "../api/auth";

export default function ProfilePage() {
  const { user, token, isAuthenticated, updateUser } = useAuth();

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    address: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) { setLoadingProfile(false); return; }
    let cancelled = false;
    (async () => {
      try {
        const data = await profileApi.get(token);
        if (!cancelled) {
          setForm({
            first_name: data.first_name || "",
            last_name: data.last_name || "",
            phone: data.phone || "",
            address: data.address || "",
          });
        }
      } catch {
        if (!cancelled && user) {
          setForm({
            first_name: user.first_name || "",
            last_name: user.last_name || "",
            phone: user.phone || "",
            address: user.address || "",
          });
        }
      } finally {
        if (!cancelled) setLoadingProfile(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token, user]);

  if (!isAuthenticated) {
    return (
      <>
        <Navbar />
        <div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
          <User size={40} className="text-gray-300 mb-4" />
          <h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Sign in to view profile</h1>
          <p className="text-gray-500 text-sm mb-6">You need an account to manage your profile.</p>
          <Link to="/login" state={{ from: { pathname: "/profile" } }} className="btn-primary">
            Sign in
          </Link>
        </div>
      </>
    );
  }

  const validate = () => {
    const errs = {};
    if (!form.first_name.trim()) errs.first_name = "First name is required.";
    if (!form.last_name.trim()) errs.last_name = "Last name is required.";
    return errs;
  };

  const set = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
    if (fieldErrors[field]) setFieldErrors((f) => ({ ...f, [field]: "" }));
    setSuccess(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const data = await profileApi.update(form, token);
      updateUser(data);
      setSuccess("Profile updated successfully!");
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(err.message || "Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  const inputClass = (field) =>
    `w-full px-4 py-3 rounded-xl border text-sm bg-white outline-none transition-colors ${
      fieldErrors[field]
        ? "border-red-300 ring-1 ring-red-200"
        : "border-gray-200 focus:border-gray-400 focus:ring-1 focus:ring-gray-200"
    }`;

  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12 animate-fade-up">
          {/* Header */}
          <div className="mb-8">
            <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">My Profile</h1>
            <p className="text-sm text-gray-500 mt-1">Update your personal information</p>
          </div>

          {/* Avatar card */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6 flex items-center gap-5 animate-fade-up animate-delay-1">
            <div className="w-16 h-16 rounded-full bg-gray-900 text-white text-xl font-semibold flex items-center justify-center shrink-0">
              {user?.first_name?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div className="min-w-0">
              <p className="font-medium text-gray-900 text-lg">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-sm text-gray-500 flex items-center gap-1.5 mt-0.5">
                <Mail size={13} />
                {user?.email}
              </p>
              {user?.role && user.role !== "customer" && (
                <span className="inline-block mt-1.5 px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full capitalize">
                  {user.role}
                </span>
              )}
            </div>
          </div>

          {/* Messages */}
          {success && (
            <div className="flex items-center gap-3 bg-green-50 border border-green-100 rounded-xl px-4 py-3 mb-6 text-sm text-green-700 animate-fade-up">
              <CheckCircle2 size={16} className="shrink-0" />
              <span>{success}</span>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700 animate-fade-up">
              <AlertCircle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loadingProfile ? (
            <div className="flex justify-center py-16">
              <Loader2 size={28} className="animate-spin text-gray-400" />
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {/* Personal info */}
              <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-5 animate-fade-up animate-delay-2">
                <h2 className="font-serif text-lg font-medium text-gray-900 flex items-center gap-2">
                  <User size={18} />
                  Personal Information
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
                    <input type="text" value={form.first_name} onChange={set("first_name")} className={inputClass("first_name")} />
                    {fieldErrors.first_name && <p className="text-xs text-red-500 mt-1">{fieldErrors.first_name}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
                    <input type="text" value={form.last_name} onChange={set("last_name")} className={inputClass("last_name")} />
                    {fieldErrors.last_name && <p className="text-xs text-red-500 mt-1">{fieldErrors.last_name}</p>}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <div className="flex items-center gap-2 px-4 py-3 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500">
                    <Mail size={15} className="shrink-0" />
                    {user?.email}
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Email cannot be changed.</p>
                </div>
              </div>

              {/* Contact info */}
              <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-5 mt-6 animate-fade-up animate-delay-3">
                <h2 className="font-serif text-lg font-medium text-gray-900 flex items-center gap-2">
                  <Phone size={18} />
                  Contact & Address
                </h2>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                  <div className="relative">
                    <Phone size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="tel"
                      value={form.phone}
                      onChange={set("phone")}
                      placeholder="e.g. 0123 456 789"
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 text-sm bg-white outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200 transition-colors"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
                  <div className="relative">
                    <MapPin size={15} className="absolute left-4 top-3.5 text-gray-400" />
                    <textarea
                      value={form.address}
                      onChange={set("address")}
                      placeholder="Street, city, country…"
                      rows={3}
                      className="w-full pl-10 pr-4 py-3 rounded-xl border border-gray-200 text-sm bg-white outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-200 transition-colors resize-none"
                    />
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="mt-6 flex justify-end animate-fade-up animate-delay-4">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 bg-gray-900 text-white px-8 py-3 rounded-xl text-sm font-medium hover:bg-gray-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                  {saving ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </>
  );
}
