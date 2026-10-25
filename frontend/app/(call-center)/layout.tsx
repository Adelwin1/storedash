import type {
  ReactNode,
} from "react";

import RoleGuard from "@/components/RoleGuard";
import StoreDashSidebar from "@/components/StoreDashSidebar";
import StoreDashTopbar from "@/components/StoreDashTopbar";


export default function CallCenterLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <RoleGuard allowedRoles={["admin", "manager", "operations"]}>
      <div className="sd-app">
        <StoreDashSidebar />

        <div className="sd-workspace">
          <StoreDashTopbar />

          <div
            className="sd-brand-background"
            aria-hidden="true"
          >
            <div className="sd-logo-watermark">
              {Array.from({ length: 13 }).map(
                (_, index) => (
                  <span
                    key={`center-${index}`}
                    className={`sd-bg-logo sd-bg-logo-${index + 1}`}
                  />
                )
              )}
            </div>

            <div className="sd-logo-cloud sd-logo-cloud-left">
              {Array.from({ length: 8 }).map(
                (_, index) => (
                  <span
                    key={`left-${index}`}
                    className="sd-bg-logo"
                  />
                )
              )}
            </div>

            <div className="sd-logo-cloud sd-logo-cloud-right">
              {Array.from({ length: 9 }).map(
                (_, index) => (
                  <span
                    key={`right-${index}`}
                    className="sd-bg-logo"
                  />
                )
              )}
            </div>
          </div>

          <main className="sd-main">
            {children}
          </main>
        </div>
      </div>
    </RoleGuard>
  );
}
