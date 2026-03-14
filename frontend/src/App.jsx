import { Routes, Route } from "react-router-dom";
import { CartProvider } from "./context/CartContext";
import { AuthProvider } from "./context/AuthContext";
import PageTransition from "./components/PageTransition";
import HomePage from "./pages/HomePage";
import CategoryPage from "./pages/CategoryPage";
import BookDetailPage from "./pages/BookDetailPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AdminBooksPage from "./pages/AdminBooksPage";
import CheckoutPage from "./pages/CheckoutPage";
import OrderHistoryPage from "./pages/OrderHistoryPage";
import ProfilePage from "./pages/ProfilePage";
import AdminOrdersPage from "./pages/AdminOrdersPage";
import AdminRevenuePage from "./pages/AdminRevenuePage";
import AdminStaffPage from "./pages/AdminStaffPage";
import AdminUsersPage from "./pages/AdminUsersPage";

export default function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <PageTransition>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/category/:id" element={<CategoryPage />} />
            <Route path="/book/:id" element={<BookDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/checkout" element={<CheckoutPage />} />
            <Route path="/orders" element={<OrderHistoryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/admin/books" element={<AdminBooksPage />} />
            <Route path="/admin/orders" element={<AdminOrdersPage />} />
            <Route path="/admin/revenue" element={<AdminRevenuePage />} />
            <Route path="/admin/staff" element={<AdminStaffPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
          </Routes>
        </PageTransition>
      </CartProvider>
    </AuthProvider>
  );
}
