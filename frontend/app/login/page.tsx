"use client";

import { Suspense } from "react";

import Link from "next/link";

import {
  FormEvent,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  api,
} from "@/lib/api";

import {
  workspaceForRole,
} from "@/lib/workspace";


function LoginPageContent() {
  const router = useRouter();
  const [
    email,
    setEmail,
  ] = useState("");

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);


  async function submit(
    event: FormEvent
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await api(
        "/auth/login",
        {
          method: "POST",

          body: JSON.stringify({
            email,
            password,
          }),
        }
      );

      const user = await api<{
        role: string;
      }>("/auth/me");

      router.replace(
        workspaceForRole(user.role)
      );

      router.refresh();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed."
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <main style={styles.page}>
      <form
        onSubmit={submit}
        style={styles.card}
      >
        <div>
          <h1 style={styles.title}>
            StoreDash
          </h1>

          <p style={styles.subtitle}>
            Employee Login
          </p>
        </div>

        <label style={styles.label}>
          Email

          <input
            style={styles.input}
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value
              )
            }
          />
        </label>

        <label style={styles.label}>
          Password

          <input
            style={styles.input}
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) =>
              setPassword(
                event.target.value
              )
            }
          />
        </label>

        {error && (
          <div style={styles.error}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={styles.button}
        >
          {loading
            ? "Logging in..."
            : "Log in"}
        </button>

        <p style={styles.footer}>
          First time here?{" "}

          <Link href="/signup">
            Create employee account
          </Link>
        </p>
      </form>
    </main>
  );
}


const styles:
Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: 24,
    background: "#f6f7f9",
    fontFamily: "Arial, sans-serif",
  },

  card: {
    width: "100%",
    maxWidth: 420,
    background: "#fff",
    padding: 32,
    borderRadius: 16,
    boxShadow:
      "0 12px 40px rgba(0,0,0,.08)",
    display: "grid",
    gap: 18,
  },

  title: {
    margin: 0,
    fontSize: 32,
  },

  subtitle: {
    margin: "6px 0 0",
    color: "#666",
  },

  label: {
    display: "grid",
    gap: 7,
    fontWeight: 600,
  },

  input: {
    padding: "12px 13px",
    borderRadius: 8,
    border: "1px solid #ccc",
    fontSize: 16,
  },

  button: {
    padding: 13,
    border: 0,
    borderRadius: 8,
    background: "#111",
    color: "#fff",
    fontSize: 16,
    cursor: "pointer",
  },

  error: {
    background: "#fff1f1",
    padding: 12,
    borderRadius: 8,
    color: "#a40000",
  },

  footer: {
    margin: 0,
    textAlign: "center",
    color: "#666",
  },
};

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
          }}
        >
          Loading StoreDash...
        </div>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}
