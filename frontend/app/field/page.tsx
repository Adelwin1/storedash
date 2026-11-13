"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { workspaceForRole } from "@/lib/workspace";

export default function FieldHomePage() {
  const router = useRouter();

  useEffect(() => {
    async function routeEmployee() {
      const user = await api<{
        role: string;
      }>("/auth/me");

      router.replace(
        workspaceForRole(user.role)
      );
    }

    void routeEmployee();
  }, [router]);

  return (
    <div className="card">
      Loading your StoreDash workspace...
    </div>
  );
}
