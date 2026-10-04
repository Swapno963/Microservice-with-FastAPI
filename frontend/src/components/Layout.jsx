import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import AuthDialog from "./AuthDialog";

export default function Layout({ children }) {
  const { isSignedIn, isAdmin, notice, openAuth, signOut, showNotice } = useAuth();
  const navigate = useNavigate();

  function onAuthClick() {
    if (isSignedIn) {
      signOut();
      showNotice("You are signed out.");
      navigate("/");
      return;
    }
    openAuth();
  }

  return (
    <>
      <header>
        <NavLink className="brand" to="/">
          ShopVerse
        </NavLink>
        <nav>
          <NavLink className={({ isActive }) => `link${isActive ? " active" : ""}`} to="/" end>
            Shop
          </NavLink>
          <NavLink className={({ isActive }) => `link${isActive ? " active" : ""}`} to="/orders">
            My orders
          </NavLink>
          {isSignedIn && (
            <NavLink className={({ isActive }) => `link${isActive ? " active" : ""}`} to="/account">
              Account
            </NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink className={({ isActive }) => `link${isActive ? " active" : ""}`} to="/admin/products">
                Products
              </NavLink>
              <NavLink className={({ isActive }) => `link${isActive ? " active" : ""}`} to="/admin/inventory">
                Inventory
              </NavLink>
            </>
          )}
          <button className="button" type="button" onClick={onAuthClick}>
            {isSignedIn ? "Sign out" : "Sign in"}
          </button>
        </nav>
      </header>
      <main>
        {notice && (
          <section className="notice" role="status">
            {notice}
          </section>
        )}
        {children}
      </main>
      <AuthDialog />
    </>
  );
}
