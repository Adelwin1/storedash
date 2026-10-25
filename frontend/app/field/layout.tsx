import Link from "next/link";
import type { ReactNode } from "react";

import RoleGuard from "@/components/RoleGuard";

export default function FieldLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleGuard allowedRoles={["admin", "manager", "supplier_field", "acquisition"]}>
      <div className="shell field-shell">

      <aside className="sidebar">

        <div className="brand">
          StoreDash
        </div>

        <div className="workspace-label">
          Supplier Acquisition
        </div>

        <nav className="nav">

          <Link href="/field/suppliers">
            Add Supplier
          </Link>

        </nav>

      </aside>


      <main className="main">
        {children}
      </main>

      </div>
    </RoleGuard>
  );
}