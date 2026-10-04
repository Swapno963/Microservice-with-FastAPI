import { useState } from "react";
import { useAuth } from "../auth";
import { money } from "../money";

const emptyAddress = {
  line1: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
};

export default function CheckoutDialog({ product, onClose, onPlaced }) {
  const { api } = useAuth();
  const [address, setAddress] = useState(emptyAddress);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  if (!product) return null;

  function update(event) {
    setAddress((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const stock = await api(
        `/api/v1/inventory/check?product_id=${encodeURIComponent(product._id)}&quantity=1`,
      );
      if (!stock.available) {
        throw new Error(stock.message || "This item is not available in the quantity you asked for.");
      }
      const order = await api("/api/v1/orders/", {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: {
          items: [{ product_id: product._id, quantity: 1, price: product.price }],
          shipping_address: address,
        },
      });
      setAddress(emptyAddress);
      onPlaced(order);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="backdrop" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-labelledby="checkout-title"
        onClick={(event) => event.stopPropagation()}
      >
        <form onSubmit={onSubmit}>
          <button type="button" className="close" aria-label="Close" onClick={onClose}>
            ×
          </button>
          <h2 id="checkout-title">Reserve your item</h2>
          <p>
            {product.name} · {money(product.price)}
          </p>
          <label>
            Address
            <input name="line1" autoComplete="street-address" required value={address.line1} onChange={update} />
          </label>
          <label>
            City
            <input name="city" autoComplete="address-level2" required value={address.city} onChange={update} />
          </label>
          <label>
            State or region
            <input name="state" autoComplete="address-level1" required value={address.state} onChange={update} />
          </label>
          <label>
            Postal code
            <input name="postal_code" autoComplete="postal-code" required value={address.postal_code} onChange={update} />
          </label>
          <label>
            Country
            <input name="country" autoComplete="country-name" required value={address.country} onChange={update} />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="button wide" type="submit" disabled={pending}>
            Place order
          </button>
          <p className="fine-print">This demo reserves stock. It does not collect payment.</p>
        </form>
      </div>
    </div>
  );
}
