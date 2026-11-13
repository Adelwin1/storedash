"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { workspaceForRole } from "@/lib/workspace";

type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};

export default function RoleGuard({
  children,
  allowedRoles,
}: {
  children: React.ReactNode;
  allowedRoles: string[];
}) {
  const router = useRouter();
  const pathname = usePathname();

  const [ready, setReady] = useState(false);
  const [forbidden, setForbidden] = useState(false);

  const allowedRolesKey = allowedRoles.join("|");

  useEffect(() => {
    let active = true;

    async function check() {
      try {
        const user = await api<CurrentUser>(
          "/auth/me"
        );

        if (!active) {
          return;
        }

        if (!allowedRoles.includes(user.role)) {
          router.replace(
            workspaceForRole(user.role)
          );
          return;
        }

        setForbidden(false);
        setReady(true);
      } catch {
        if (active) {
          router.replace(
            `/login?next=${encodeURIComponent(pathname)}`
          );
        }
      }
    }

    void check();

    return () => {
      active = false;
    };
  }, [
    pathname,
    router,
    allowedRolesKey,
  ]);

  if (forbidden) {
    return (
      <div className="sd-access-screen">
        <div className="sd-access-logo">S</div>

        <strong>Access denied</strong>

        <span>
          Your StoreDash role does not have access
          to this workspace.
        </span>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="sd-access-screen">
        <div className="sd-access-logo">S</div>

        <strong>StoreDash</strong>

        <span>Checking access...</span>
      </div>
    );
  }

  return <>{children}</>;
}
