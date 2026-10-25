"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Supplier } from "@/lib/types";

export default function SuppliersPage() {
  const [query, setQuery] = useState("");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [message, setMessage] = useState("");

  async function searchSuppliers() {
    try {
      const data = await api<Supplier[]>(`/suppliers?q=${encodeURIComponent(query)}`);
      setSuppliers(data);
      setMessage(data.length ? "" : "No supplier found.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed");
    }
  }

  return (
    <>
      <div className="header">

  <div>

    <h1>
      Suppliers
    </h1>

    <p className="label">
      Search a wholesaler or retailer by
      StoreDash supplier number,
      name, phone or category.
    </p>

  </div>


  <Link
    className="btn"
    href="/suppliers/new"
  >
    + Register Supplier
  </Link>

</div>

      <div className="card">
        <h2>Find supplier</h2>
        <div className="toolbar">
          <input
            className="input"
            style={{ maxWidth: 560 }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") searchSuppliers(); }}
            placeholder="Supplier #000, name, phone or category"
          />
          <button className="btn" onClick={searchSuppliers}>Search</button>
        </div>
        {message && <div className="notice">{message}</div>}
        {suppliers.length > 0 && (
          <table className="table" style={{ marginTop: 12 }}>
            <thead><tr><th>#</th><th>Supplier</th><th>Category</th><th>Phone</th><th>Location</th><th></th></tr></thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td><span className="number-badge">{supplier.supplier_number}</span></td>
                  <td>{supplier.name}</td>
                  <td>{supplier.category || "—"}</td>
                  <td>{supplier.phone}</td>
                  <td>{supplier.location || supplier.landmark || "—"}</td>
                  <td><Link className="text-link" href={`/suppliers/${supplier.id}`}>View profile →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
