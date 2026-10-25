"use client";

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


export default function SignupPage() {
  const router = useRouter();

  const [
    name,
    setName,
  ] = useState("");

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    phone,
    setPhone,
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
        "/auth/signup",
        {
          method: "POST",

          body: JSON.stringify({
            name,
            email,

            phone:
              phone.trim() ||
              null,

            password,
          }),
        }
      );

      router.replace(
        "/dashboard"
      );

      router.refresh();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Signup failed."
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
            Create Employee Account
          </p>
        </div>

        <p style={styles.notice}>
          Your email must already be
          approved by StoreDash.
        </p>

        <label style={styles.label}>
          Full name

          <input
            style={styles.input}
            required
            value={name}
            onChange={(event) =>
              setName(
                event.target.value
              )
            }
          />
        </label>

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
          Phone
          <span
            style={{
              color: "#888",
              fontWeight: 400,
            }}
          >
            optional
          </span>

          <input
            style={styles.input}
            value={phone}
            onChange={(event) =>
              setPhone(
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
            minLength={10}
            autoComplete="new-password"
            value={password}
            onChange={(event) =>
              setPassword(
                event.target.value
              )
            }
          />
        </label>

        <small>
          Minimum 10 characters.
        </small>

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
            ? "Creating account..."
            : "Create account"}
        </button>

        <p style={styles.footer}>
          Already registered?{" "}

          <Link href="/login">
            Log in
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
    maxWidth: 440,
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

  notice: {
    background: "#f3f5f7",
    borderRadius: 8,
    padding: 12,
    margin: 0,
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
