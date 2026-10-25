"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  usePathname,
} from "next/navigation";

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


export default function AuthGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const [
    ready,
    setReady,
  ] = useState(false);


  useEffect(() => {
    let active = true;

    const timeout =
      window.setTimeout(() => {
        if (!active) {
          return;
        }

        window.location.replace(
          `/login?next=${encodeURIComponent(
            pathname
          )}`
        );
      }, 5000);


    async function check() {
      try {
        await api<CurrentUser>(
          "/auth/me"
        );

        if (active) {
          window.clearTimeout(
            timeout
          );

          setReady(true);
        }

      } catch {
        if (active) {
          window.clearTimeout(
            timeout
          );

          window.location.replace(
            `/login?next=${encodeURIComponent(
              pathname
            )}`
          );
        }
      }
    }


    void check();


    return () => {
      active = false;

      window.clearTimeout(
        timeout
      );
    };
  }, [
    pathname,
  ]);


  if (!ready) {
    return (
      <div className="sd-access-screen">
        <div className="sd-access-logo">
          S
        </div>

        <strong>
          StoreDash
        </strong>

        <span>
          Checking access...
        </span>
      </div>
    );
  }


  return <>{children}</>;
}
