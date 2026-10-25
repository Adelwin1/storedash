"use client";

import {
  LogOut,
} from "lucide-react";

import {
  useRouter,
} from "next/navigation";

import {
  api,
} from "@/lib/api";


export default function LogoutButton() {
  const router = useRouter();


  async function logout() {
    try {
      await api(
        "/auth/logout",
        {
          method: "POST",
        }
      );
    } finally {
      router.replace(
        "/login"
      );

      router.refresh();
    }
  }


  return (
    <button
      type="button"
      onClick={logout}
      className="sd-logout"
    >
      <LogOut size={18} />

      <span>
        Log out
      </span>
    </button>
  );
}
