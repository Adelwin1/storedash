"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};

export default function AdminEmployeesLink() {
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const user = await api<CurrentUser>(
          "/auth/me"
        );

        setIsAdmin(
          user.role === "admin"
        );
      } catch {
        setIsAdmin(false);
      }
    }

    void load();
  }, []);

  if (!isAdmin) {
    return null;
  }

  return (
    <Link href="/employees">
      Employees
    </Link>
  );
}
