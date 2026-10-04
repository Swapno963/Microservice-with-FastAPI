import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { money } from "../money";

const emptyProduct = {
  name: "",
  description: "",
  category: "",
  price: "",
  quantity: "",
};

export default function AdminProducts() {
  const { api, isAdmin, showNotice } = useAuth();
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(emptyProduct);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    setProducts(await api("/api/v1/products/"));
  }

  useEffect(() => {
    if (!isAdmin) return;
    load().catch((err) => setError(err.message));
  }, [isAdmin]);

  if (!isAdmin) {
    return <p className="empty">Product management is available to merchant accounts.</p>;
  }

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function createProduct(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/products/", {
        method: "POST",
        body: {
          name: form.name,
          description: form.description,
          category: form.category,
          price: Number(form.price),
          quantity: Number(form.quantity),
        },
      });
      setForm(emptyProduct);
      await load();
      showNotice("Product created.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveEdit(event) {
    event.preventDefault();
    setError("");
    const body = {};
    for (const key of ["name", "description", "category"]) {
      if (editing[key]) body[key] = editing[key];
    }
    if (editing.price !== "" && editing.price != null) body.price = Number(editing.price);
    if (editing.quantity !== "" && editing.quantity != null) body.quantity = Number(editing.quantity);
    try {
      await api(`/api/v1/products/${editing._id}`, { method: "PUT", body });
      setEditing(null);
      await load();
      showNotice("Product updated.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(product) {
    if (!window.confirm(`Delete ${product.name}?`)) return;
    setError("");
    try {
      await api(`/api/v1/products/${product._id}`, { method: "DELETE" });
      await load();
      showNotice("Product deleted.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Merchant</p>
          <h1>Products</h1>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <form className="panel stack" onSubmit={createProduct}>
        <h2>New product</h2>
        <label>
          Name
          <input name="name" required value={form.name} onChange={update} />
        </label>
        <label>
          Description
          <textarea name="description" required value={form.description} onChange={update} />
        </label>
        <label>
          Category
          <input name="category" required value={form.category} onChange={update} />
        </label>
        <label>
          Price
          <input name="price" type="number" min="0.01" step="0.01" required value={form.price} onChange={update} />
        </label>
        <label>
          Starting quantity
          <input name="quantity" type="number" min="0" step="1" required value={form.quantity} onChange={update} />
        </label>
        <button className="button" type="submit">
          Create product
        </button>
      </form>
      <div className="product-grid">
        {products.map((product) => (
          <article className="product-card" key={product._id}>
            <p className="eyebrow">{product.category}</p>
            <h2>{product.name}</h2>
            <p>{product.description}</p>
            <p className="price">{money(product.price)}</p>
            <p className="muted">Catalog quantity {product.quantity}</p>
            <div className="row-actions">
              <button className="button secondary" type="button" onClick={() => setEditing({ ...product })}>
                Edit
              </button>
              <button className="button danger" type="button" onClick={() => remove(product)}>
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
      {editing && (
        <div className="backdrop" onClick={() => setEditing(null)}>
          <div className="modal" role="dialog" aria-labelledby="edit-title" onClick={(event) => event.stopPropagation()}>
            <form onSubmit={saveEdit}>
              <button type="button" className="close" aria-label="Close" onClick={() => setEditing(null)}>
                ×
              </button>
              <h2 id="edit-title">Edit product</h2>
              <label>
                Name
                <input value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} />
              </label>
              <label>
                Description
                <textarea
                  value={editing.description}
                  onChange={(event) => setEditing({ ...editing, description: event.target.value })}
                />
              </label>
              <label>
                Category
                <input
                  value={editing.category}
                  onChange={(event) => setEditing({ ...editing, category: event.target.value })}
                />
              </label>
              <label>
                Price
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={editing.price}
                  onChange={(event) => setEditing({ ...editing, price: event.target.value })}
                />
              </label>
              <label>
                Quantity
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={editing.quantity}
                  onChange={(event) => setEditing({ ...editing, quantity: event.target.value })}
                />
              </label>
              <button className="button" type="submit">
                Save changes
              </button>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
