import { useEffect, useState } from "react";
import { useAuth } from "../auth";

export default function AdminInventory() {
  const { api, isAdmin, showNotice } = useAuth();
  const [items, setItems] = useState([]);
  const [names, setNames] = useState({});
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [productId, setProductId] = useState("");
  const [quantityChange, setQuantityChange] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const params = new URLSearchParams();
    if (lowStockOnly) params.set("low_stock_only", "true");
    const [inventory, products] = await Promise.all([
      api(`/api/v1/inventory/${params.toString() ? `?${params}` : ""}`),
      api("/api/v1/products/?limit=100"),
    ]);
    setItems(inventory);
    setNames(Object.fromEntries(products.map((product) => [product._id, product.name])));
  }

  useEffect(() => {
    if (!isAdmin) return;
    load().catch((err) => setError(err.message));
  }, [isAdmin, lowStockOnly]);

  if (!isAdmin) {
    return <p className="empty">Inventory adjustments are available to merchant accounts.</p>;
  }

  async function adjust(event) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/v1/inventory/adjust", {
        method: "POST",
        body: {
          product_id: productId,
          quantity_change: Number(quantityChange),
          reason,
        },
      });
      setQuantityChange("");
      setReason("");
      await load();
      showNotice("Inventory adjusted.");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Merchant</p>
          <h1>Inventory</h1>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <form className="panel stack" onSubmit={adjust}>
        <h2>Adjust stock</h2>
        <label>
          Product
          <select required value={productId} onChange={(event) => setProductId(event.target.value)}>
            <option value="">Choose a product</option>
            {items.map((item) => (
              <option key={item.product_id} value={item.product_id}>
                {names[item.product_id] || item.product_id}
              </option>
            ))}
          </select>
        </label>
        <label>
          Quantity change
          <input
            type="number"
            step="1"
            required
            value={quantityChange}
            onChange={(event) => setQuantityChange(event.target.value)}
            placeholder="5 to add, -2 to remove"
          />
        </label>
        <label>
          Reason
          <input
            required
            minLength={3}
            maxLength={200}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <button className="button" type="submit">
          Apply adjustment
        </button>
      </form>
      <label className="check">
        <input
          type="checkbox"
          checked={lowStockOnly}
          onChange={(event) => setLowStockOnly(event.target.checked)}
        />
        Low stock only
      </label>
      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Available</th>
              <th>Reserved</th>
              <th>Reorder at</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{names[item.product_id] || item.product_id}</td>
                <td>{item.available_quantity}</td>
                <td>{item.reserved_quantity}</td>
                <td>{item.reorder_threshold}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <p className="muted">No inventory rows match this view.</p>}
      </div>
    </section>
  );
}
