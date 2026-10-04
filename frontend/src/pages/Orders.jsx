import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { money } from "../money";

export default function Orders() {
  const { api, isSignedIn, openAuth } = useAuth();
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      setOrders(await api("/api/v1/orders/"));
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isSignedIn) load();
  }, [isSignedIn]);

  const pendingIds = orders
    .filter((order) => order.reservation_state === "pending")
    .map((order) => order._id)
    .join(",");

  useEffect(() => {
    if (!pendingIds) return undefined;
    const timer = window.setInterval(async () => {
      const ids = pendingIds.split(",");
      try {
        const updates = await Promise.all(ids.map((id) => api(`/api/v1/orders/${id}`)));
        setOrders((current) =>
          current.map((order) => updates.find((next) => next._id === order._id) || order),
        );
      } catch {
        // The next tick retries. A failed poll should not wipe the list.
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [api, pendingIds]);

  async function cancelOrder(orderId) {
    try {
      await api(`/api/v1/orders/${orderId}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Your purchases</p>
          <h1>Orders</h1>
        </div>
        {isSignedIn && (
          <button className="button secondary" type="button" onClick={load}>
            Refresh
          </button>
        )}
      </div>
      {!isSignedIn && (
        <p className="empty">
          Sign in to see your orders.{" "}
          <button className="link" type="button" onClick={openAuth}>
            Sign in
          </button>
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {loading && <p>Loading orders…</p>}
      {isSignedIn && !loading && orders.length === 0 && !error && (
        <p className="empty">You have no orders yet.</p>
      )}
      <div className="order-list">
        {orders.map((order) => {
          const reservation = order.reservation_state || "pending";
          const canCancel = reservation === "pending" || reservation === "reserved";
          return (
            <article className="order-card" key={order._id}>
              <div>
                <span className={`status ${reservation}`}>{reservation}</span>
                <h2>
                  {order.items.length} item{order.items.length === 1 ? "" : "s"}
                </h2>
                <p>
                  {money(order.total_price)} · {order.status} · Order {order._id}
                </p>
              </div>
              {canCancel && (
                <button className="button secondary" type="button" onClick={() => cancelOrder(order._id)}>
                  Cancel
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
