"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Order, Supplier } from "@/lib/types";
import LocationPicker from "@/components/LocationPicker";

function money(value: string | number | null | undefined) {
  return `GH₵${Number(value || 0).toFixed(2)}`;
}

export default function SupplierProfilePage() {
  const params = useParams<{ id: string }>();
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [supplierData, orderData] = await Promise.all([
          api<Supplier>(`/suppliers/${params.id}`),
          api<Order[]>(`/orders?supplier_id=${params.id}`)
        ]);
        setSupplier(supplierData);
        setOrders(orderData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load supplier");
      }
    }
    if (params.id) load();
  }, [params.id]);

  if (error) return <div className="card"><div className="error">{error}</div></div>;
  if (!supplier) return <div className="card">Loading supplier…</div>;

  return (
    <>
      <div className="header">
        <div>
          <div className="eyebrow">Supplier #{supplier.supplier_number}</div>
          <h1>{supplier.name}</h1>
          <p className="label">{supplier.category || "Supplier"} · {supplier.phone}</p>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h2>Supplier details</h2>
          <dl className="details-list">
            <div><dt>Supplier number</dt><dd>#{supplier.supplier_number}</dd></div>
            <div><dt>Name</dt><dd>{supplier.name}</dd></div>
            <div><dt>Category</dt><dd>{supplier.category || "—"}</dd></div>
            <div><dt>Phone</dt><dd>{supplier.phone}</dd></div>
            <div><dt>Contact person</dt><dd>{supplier.contact_person || "—"}</dd></div>
            <div><dt>Location</dt><dd>{supplier.location || "—"}</dd></div>
            <div><dt>Landmark</dt><dd>{supplier.landmark || "—"}</dd></div>
            <div><dt>Pickup notes</dt><dd>{supplier.pickup_notes || "—"}</dd></div>
            <div><dt>Taking StoreDash orders</dt><dd>{supplier.willing_to_fulfill ? "Yes" : "No"}</dd></div>
          </dl>

          <LocationPicker
            entityType="supplier"
            entityId={supplier.id}
            initialLocation={
              supplier.location
            }
            onSaved={(location) => {
              setSupplier({
                ...supplier,
                location,
              });
            }}
          />
        </div>

        <div className="card">
          <h2>Supplier history</h2>
          <div className="label">Transactions using this supplier</div>
          <div className="metric">{orders.length}</div>
          <p className="label" style={{ marginTop: 18 }}>As sourcing data grows, this page can later show prices, availability hit rate, preparation time and reliability.</p>
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h2>Transaction history</h2>
        {orders.length === 0 ? (
          <div className="empty-state">No orders have been assigned to this supplier yet.</div>
        ) : (
          <table className="table">
            <thead><tr><th>Order</th><th>Date</th><th>Status</th><th>Items from supplier</th><th>Confirmed value</th></tr></thead>
            <tbody>
              {orders.map((order) => {
                const items = order.items.filter((item) => item.supplier_id === supplier.id);
                const value = items.reduce((sum, item) => sum + Number(item.confirmed_price || 0), 0);
                return (
                  <tr key={order.id}>
                    <td>{order.order_number}</td>
                    <td>{new Date(order.created_at).toLocaleDateString()}</td>
                    <td><span className="badge">{order.status.replaceAll("_", " ")}</span></td>
                    <td>{items.map((item) => `${item.name} ×${item.confirmed_quantity ?? item.requested_quantity}`).join(", ")}</td>
                    <td>{money(value)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
