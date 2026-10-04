import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import CheckoutDialog from "../components/CheckoutDialog";
import { money } from "../money";

export default function Catalog() {
  const { api, isSignedIn, openAuth, showNotice } = useAuth();
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let ignore = false;
    api("/api/v1/products/category/list")
      .then((list) => {
        if (!ignore) setCategories(list);
      })
      .catch(() => {
        if (!ignore) setCategories([]);
      });
    return () => {
      ignore = true;
    };
  }, [api]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (name.trim()) params.set("name", name.trim());
    if (category) params.set("category", category);
    const query = params.toString();
    let ignore = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api(`/api/v1/products/${query ? `?${query}` : ""}`)
        .then((list) => {
          if (!ignore) {
            setProducts(list);
            setError("");
          }
        })
        .catch((err) => {
          if (!ignore) setError(err.message);
        })
        .finally(() => {
          if (!ignore) setLoading(false);
        });
    }, 250);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [api, name, category]);

  function reserve(product) {
    if (!isSignedIn) {
      showNotice("Sign in before placing an order.");
      openAuth();
      return;
    }
    setSelected(product);
  }

  return (
    <section>
      <div className="hero">
        <p className="eyebrow">Simple shopping</p>
        <h1>Find what you need.</h1>
        <p>Stock is held after checkout. We will show you when your reservation is confirmed.</p>
      </div>
      <div className="filters">
        <label>
          Search
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Product name" />
        </label>
        <label>
          Category
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      {loading && <p>Loading products…</p>}
      {!loading && products.length === 0 && !error && <p className="empty">No products are available yet.</p>}
      <div className="product-grid">
        {products.map((product) => (
          <article className="product-card" key={product._id}>
            <p className="eyebrow">{product.category}</p>
            <h2>{product.name}</h2>
            <p>{product.description}</p>
            <p className="price">{money(product.price)}</p>
            <button className="button" type="button" onClick={() => reserve(product)}>
              Reserve item
            </button>
          </article>
        ))}
      </div>
      <CheckoutDialog
        product={selected}
        onClose={() => setSelected(null)}
        onPlaced={(order) => {
          setSelected(null);
          showNotice(`Order ${order._id} is pending. We are reserving your stock now.`);
          navigate("/orders");
        }}
      />
    </section>
  );
}
