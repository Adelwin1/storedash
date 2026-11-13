"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import RoleGuard from "@/components/RoleGuard";
import { api } from "@/lib/api";

type CurrentUser = {
  role: string;
};

export default function FieldLayout({
  children,
}: {
  children: ReactNode;
}) {
  const [role, setRole] = useState("");

  useEffect(() => {
    async function loadUser() {
      try {
        const user =
          await api<CurrentUser>("/auth/me");

        setRole(user.role);
      } catch {
        // RoleGuard handles authentication.
      }
    }

    void loadUser();
  }, []);

  const canSuppliers =
    role === "supplier_field"
    || role === "acquisition"
    || role === "manager"
    || role === "admin";

  const canCustomers =
    role === "customer_field"
    || role === "acquisition"
    || role === "manager"
    || role === "admin";

  return (
    <RoleGuard
      allowedRoles={[
        "admin",
        "manager",
        "supplier_field",
        "customer_field",
        "acquisition",
      ]}
    >
      <div className="shell field-shell">
        <aside className="sidebar">
          <div className="brand">
            StoreDash
          </div>

          <div className="workspace-label">
            {role === "customer_field"
              ? "Customer Acquisition"
              : role === "supplier_field"
                ? "Supplier Acquisition"
                : "Field Operations"}
          </div>

          <nav className="nav">
            {canSuppliers && (
              <Link href="/field/suppliers">
                Add Supplier
              </Link>
            )}

            {canCustomers && (
              <Link href="/field/customers">
                Add Customer
              </Link>
            )}
          </nav>
        </aside>

        <main className="main">
          {children}
        </main>
      </div>
    </RoleGuard>
  );
}
