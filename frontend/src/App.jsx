import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Account from "./pages/Account";
import AdminInventory from "./pages/AdminInventory";
import AdminProducts from "./pages/AdminProducts";
import Catalog from "./pages/Catalog";
import Orders from "./pages/Orders";

function AdminRoute({ children }) {
  const { isSignedIn, isAdmin, openAuth } = useAuth();
  if (!isSignedIn) {
    return (
      <p className="empty">
        Sign in with a merchant account.{" "}
        <button className="link" type="button" onClick={openAuth}>
          Sign in
        </button>
      </p>
    );
  }
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Catalog />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/account" element={<Account />} />
        <Route
          path="/admin/products"
          element={
            <AdminRoute>
              <AdminProducts />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/inventory"
          element={
            <AdminRoute>
              <AdminInventory />
            </AdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
