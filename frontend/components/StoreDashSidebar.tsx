"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import {
  usePathname,
} from "next/navigation";

import {
  LayoutDashboard,
  ClipboardList,
  PlusCircle,
  UsersRound,
  Store,
  Truck,
  Send,
  UserCog,
  WalletCards,
  ArrowRight,
} from "lucide-react";

import {
  api,
} from "@/lib/api";

import LogoutButton from "@/components/LogoutButton";


type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};


const primaryLinks = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
  {
    href: "/orders",
    label: "Orders",
    icon: ClipboardList,
  },
  {
    href: "/orders/new",
    label: "New Order",
    icon: PlusCircle,
  },
  {
    href: "/customers",
    label: "Customers",
    icon: UsersRound,
  },
  {
    href: "/suppliers",
    label: "Suppliers",
    icon: Store,
  },
  {
    href: "/drivers",
    label: "Drivers",
    icon: Truck,
  },
  {
    href: "/dispatch",
    label: "Dispatch",
    icon: Send,
  },
  {
    href: "/payments",
    label: "Payments",
    icon: WalletCards,
  },
];


export default function StoreDashSidebar() {
  const pathname = usePathname();

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


  function active(
    href: string
  ) {
    if (href === "/dashboard") {
      return pathname === href;
    }

    if (href === "/orders") {
      return pathname === "/orders";
    }

    return pathname.startsWith(
      href
    );
  }


  return (
    <aside className="sd-sidebar">
      <div className="sd-logo-row">
        <div className="sd-logo-mark">
          <span />
          <span />
          <span />
        </div>

        <div className="sd-logo-text">
          StoreDash
        </div>
      </div>


      <nav className="sd-nav">
        {primaryLinks.map(
          ({
            href,
            label,
            icon: Icon,
          }) => (
            <Link
              key={href}
              href={href}
              className={
                active(href)
                  ? "sd-nav-item sd-nav-active"
                  : "sd-nav-item"
              }
            >
              <Icon
                size={20}
                strokeWidth={2}
              />

              <span>
                {label}
              </span>

              {label === "Orders" && (
                <span className="sd-nav-badge">
                  •
                </span>
              )}
            </Link>
          )
        )}


        {user?.role === "admin" && (
          <Link
            href="/employees"
            className={
              active("/employees")
                ? "sd-nav-item sd-nav-active"
                : "sd-nav-item"
            }
          >
            <UserCog
              size={20}
              strokeWidth={2}
            />

            <span>
              Employees
            </span>
          </Link>
        )}
      </nav>


      <div className="sd-sidebar-grow" />


      <div className="sd-community-card">
        <div className="sd-community-illustration">
          <div className="mini-roof" />
          <div className="mini-store">
            <div />
            <div />
          </div>
        </div>

        <div className="sd-community-copy">
          Powering local stores,
          <br />
          happier communities.
        </div>

        <Link
          href="/customers"
          className="sd-community-arrow"
        >
          <ArrowRight size={17} />
        </Link>
      </div>


      {user && (
        <div className="sd-sidebar-user">
          <div className="sd-sidebar-avatar">
            {user.name
              .trim()
              .charAt(0)
              .toUpperCase()}
          </div>

          <div>
            <strong>
              {user.name}
            </strong>

            <span>
              {user.role}
            </span>
          </div>
        </div>
      )}

      <LogoutButton />
    </aside>
  );
}
