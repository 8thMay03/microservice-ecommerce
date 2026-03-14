import { useState, useEffect, useCallback } from "react";
import {
  UserCog, Loader2, AlertCircle, RefreshCw, Plus,
  Trash2, X, Mail, Phone, Save,
} from "lucide-react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import { adminStaffApi } from "../api/admin";

export default function AdminStaffPage() {
  const { user, token, isAuthenticated } = useAuth();
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ email: "", password: "", password_confirm: "", first_name: "", last_name: "", phone: "", department: "" });
  const [addError, setAddError] = useState(null);
  const [adding, setAdding] = useState(false);

  const isAdmin = user?.role === "manager";

  const fetchStaff = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await adminStaffApi.list(token);
      setStaff(Array.isArray(data) ? data : data.results ?? []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { if (token) fetchStaff(); }, [fetchStaff, token]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!addForm.email || !addForm.password || !addForm.first_name || !addForm.last_name) { setAddError("Fill in all required fields."); return; }
    if (addForm.password !== addForm.password_confirm) { setAddError("Passwords do not match."); return; }
    setAdding(true); setAddError(null);
    try {
      await adminStaffApi.create(addForm, token);
      setShowAdd(false);
      setAddForm({ email: "", password: "", password_confirm: "", first_name: "", last_name: "", phone: "", department: "" });
      fetchStaff();
    } catch (e) { setAddError(e.message); }
    finally { setAdding(false); }
  };

  const handleDeactivate = async (id) => {
    if (!confirm("Deactivate this staff member?")) return;
    try {
      await adminStaffApi.deactivate(id, token);
      setStaff((prev) => prev.filter((s) => s.id !== id));
    } catch { /* ignore */ }
  };

  if (!isAuthenticated || !isAdmin) {
    return (<><Navbar /><div className="min-h-[60vh] flex flex-col items-center justify-center bg-stone-50 px-4">
      <UserCog size={40} className="text-gray-300 mb-4" /><h1 className="font-serif text-2xl font-medium text-gray-900 mb-2">Admin Access Required</h1></div></>);
  }

  return (
    <><Navbar />
      <main className="min-h-screen bg-stone-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 animate-fade-up">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="font-serif text-2xl sm:text-3xl font-medium text-gray-900">Staff Management</h1>
              <p className="text-sm text-gray-500 mt-1">{staff.length} staff member{staff.length !== 1 ? "s" : ""}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-700 transition-colors">
                <Plus size={16} /> Add Staff
              </button>
              <button onClick={fetchStaff} disabled={loading}
                className="p-2.5 rounded-xl border border-gray-200 bg-white text-gray-500 hover:text-gray-900 transition-colors disabled:opacity-50">
                <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              </button>
            </div>
          </div>

          {error && <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6 text-sm text-red-700"><AlertCircle size={16} />{error}</div>}

          {/* Add form modal */}
          {showAdd && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 animate-fade-up">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-medium">Add New Staff</h2>
                <button onClick={() => setShowAdd(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
              </div>
              {addError && <div className="flex items-center gap-2 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mb-4 text-sm text-red-700"><AlertCircle size={14} />{addError}</div>}
              <form onSubmit={handleAdd} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input value={addForm.first_name} onChange={(e) => setAddForm({...addForm, first_name: e.target.value})} placeholder="First Name *"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                  <input value={addForm.last_name} onChange={(e) => setAddForm({...addForm, last_name: e.target.value})} placeholder="Last Name *"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                </div>
                <input value={addForm.email} onChange={(e) => setAddForm({...addForm, email: e.target.value})} type="email" placeholder="Email *"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input value={addForm.password} onChange={(e) => setAddForm({...addForm, password: e.target.value})} type="password" placeholder="Password *"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                  <input value={addForm.password_confirm} onChange={(e) => setAddForm({...addForm, password_confirm: e.target.value})} type="password" placeholder="Confirm Password *"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <input value={addForm.phone} onChange={(e) => setAddForm({...addForm, phone: e.target.value})} placeholder="Phone"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                  <input value={addForm.department} onChange={(e) => setAddForm({...addForm, department: e.target.value})} placeholder="Department"
                    className="px-4 py-3 rounded-xl border border-gray-200 text-sm outline-none focus:border-gray-400" />
                </div>
                <button type="submit" disabled={adding}
                  className="flex items-center gap-2 px-6 py-3 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-700 disabled:opacity-60 transition-colors">
                  {adding ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} {adding ? "Creating…" : "Create Staff"}
                </button>
              </form>
            </div>
          )}

          {loading && staff.length === 0 ? (
            <div className="flex justify-center py-20"><Loader2 size={28} className="animate-spin text-gray-400" /></div>
          ) : staff.length === 0 ? (
            <div className="text-center py-20 text-gray-400"><UserCog size={28} className="mx-auto mb-2 opacity-50" /><p className="text-sm">No staff members yet.</p></div>
          ) : (
            <div className="space-y-3">
              {staff.map((s) => (
                <div key={s.id} className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-gray-900 text-white text-sm font-semibold flex items-center justify-center shrink-0">
                    {(s.first_name || "?").charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{s.first_name} {s.last_name}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                      <span className="flex items-center gap-1"><Mail size={11} />{s.email}</span>
                      {s.phone && <span className="flex items-center gap-1"><Phone size={11} />{s.phone}</span>}
                      {s.department && <span className="px-2 py-0.5 bg-gray-100 rounded text-gray-600">{s.department}</span>}
                    </div>
                  </div>
                  <button onClick={() => handleDeactivate(s.id)} className="p-2 text-gray-400 hover:text-red-500 transition-colors" title="Deactivate">
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
