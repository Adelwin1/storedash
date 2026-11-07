"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import {
  Bell,
  Search,
  ChevronDown,
} from "lucide-react";

import {
  api,
} from "@/lib/api";


type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};


export default function StoreDashTopbar() {
  const [
    user,
    setUser,
  ] = useState<CurrentUser | null>(
    null
  );


  useEffect(() => {
    async function loadUser() {
      try {
        const data =
          await api<CurrentUser>(
            "/auth/me"
          );

        setUser(data);

      } catch {
        setUser(null);
      }
    }

    void loadUser();
  }, []);


  return (
    <header className="sd-topbar">
      <Link
        href="/orders"
        className="sd-search"
      >
        <Search
          size={19}
          strokeWidth={2}
        />

        <span>
          Search orders, customers,
          drivers, or anything...
        </span>

        <kbd>
          ⌘ K
        </kbd>
      </Link>


      <div className="sd-topbar-actions">
        <button
          type="button"
          className="sd-icon-button"
          aria-label="Notifications"
        >
          <Bell size={19} />

          <span className="sd-notification-dot">
            3
          </span>
        </button>


        {user && (
          <div className="sd-profile">
            <div className="sd-profile-avatar">
              {user.name
                .trim()
                .charAt(0)
                .toUpperCase()}
            </div>

            <div className="sd-profile-copy">
              <strong>
                {user.name}
              </strong>

              <span>
                {user.role === "admin"
                  ? "Administrator"
                  : user.role === "manager"
                    ? "StoreDash Manager"
                    : "StoreDash Operator"}
              </span>
            </div>

            <ChevronDown
              size={16}
            />
          </div>
        )}
      </div>
    </header>
  );
}
