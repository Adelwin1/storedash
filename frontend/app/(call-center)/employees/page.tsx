"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

type CurrentUser = {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
};

type Employee = {
  id: number;
  email: string;
  name: string | null;
  role: string;
  is_active: boolean;
  claimed_user_id: number | null;
};

export default function EmployeesPage() {
  const router = useRouter();

  const [employees, setEmployees] =
    useState<Employee[]>([]);

  const [name, setName] =
    useState("");

  const [email, setEmail] =
    useState("");

  const [role, setRole] =
    useState("operations");

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");

  async function loadEmployees() {
    const data = await api<Employee[]>(
      "/auth/approved-employees"
    );

    setEmployees(data);
  }

  useEffect(() => {
    async function start() {
      try {
        const user =
          await api<CurrentUser>(
            "/auth/me"
          );

        if (user.role !== "admin") {
          router.replace(
            "/dashboard"
          );

          return;
        }

        await loadEmployees();

      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Could not load employees."
        );
      } finally {
        setLoading(false);
      }
    }

    void start();
  }, [router]);

  async function addEmployee(
    event: FormEvent
  ) {
    event.preventDefault();

    setError("");
    setMessage("");
    setSaving(true);

    try {
      await api(
        "/auth/approved-employees",
        {
          method: "POST",

          body: JSON.stringify({
            name:
              name.trim() || null,

            email,

            role,
          }),
        }
      );

      setName("");
      setEmail("");
      setRole("operations");

      setMessage(
        "Employee email approved."
      );

      await loadEmployees();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not approve employee."
      );
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(
    employee: Employee
  ) {
    if (
      !window.confirm(
        `Deactivate ${employee.email}?`
      )
    ) {
      return;
    }

    setError("");
    setMessage("");

    try {
      await api(
        `/auth/approved-employees/${employee.id}/deactivate`,
        {
          method: "POST",
        }
      );

      setMessage(
        `${employee.email} deactivated.`
      );

      await loadEmployees();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not deactivate employee."
      );
    }
  }

  if (loading) {
    return (
      <div>
        Loading employees...
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: 1000,
      }}
    >
      <h1>Employees</h1>

      <p
        style={{
          color: "#666",
        }}
      >
        Only approved emails can create
        StoreDash employee accounts.
      </p>

      <form
        onSubmit={addEmployee}
        style={{
          maxWidth: 600,
          display: "grid",
          gap: 14,
          padding: 20,
          border:
            "1px solid #ddd",
          borderRadius: 12,
          marginTop: 24,
          marginBottom: 30,
        }}
      >
        <h2
          style={{
            margin: 0,
          }}
        >
          Add Employee
        </h2>

        <label>
          Name

          <input
            value={name}
            onChange={(e) =>
              setName(e.target.value)
            }
            style={{
              width: "100%",
              padding: 10,
              marginTop: 5,
            }}
          />
        </label>

        <label>
          Email

          <input
            type="email"
            required
            value={email}
            onChange={(e) =>
              setEmail(e.target.value)
            }
            style={{
              width: "100%",
              padding: 10,
              marginTop: 5,
            }}
          />
        </label>

        <label>
          Role

          <select
            value={role}
            onChange={(e) =>
              setRole(e.target.value)
            }
            style={{
              width: "100%",
              padding: 10,
              marginTop: 5,
            }}
          >
            <option value="operations">
              Operations
            </option>

            <option value="manager">
              Manager
            </option>

            <option value="supplier_field">
              Supplier Field
            </option>

            <option value="customer_field">
              Customer Field
            </option>

            <option value="acquisition">
              Acquisition
            </option>
          </select>
        </label>

        <button
          type="submit"
          disabled={saving}
          className="btn"
        >
          {saving
            ? "Approving..."
            : "Approve Employee"}
        </button>
      </form>

      {error && (
        <div
          style={{
            marginBottom: 15,
            color: "#a40000",
          }}
        >
          {error}
        </div>
      )}

      {message && (
        <div
          style={{
            marginBottom: 15,
          }}
        >
          {message}
        </div>
      )}

      <div
        style={{
          overflowX: "auto",
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse:
              "collapse",
          }}
        >
          <thead>
            <tr>
              <th style={th}>
                Name
              </th>

              <th style={th}>
                Email
              </th>

              <th style={th}>
                Role
              </th>

              <th style={th}>
                Access
              </th>

              <th style={th}>
                Account
              </th>

              <th style={th}>
                Action
              </th>
            </tr>
          </thead>

          <tbody>
            {employees.map(
              (employee) => (
                <tr
                  key={
                    employee.id
                  }
                >
                  <td style={td}>
                    {employee.name ||
                      "—"}
                  </td>

                  <td style={td}>
                    {employee.email}
                  </td>

                  <td style={td}>
                    {employee.role}
                  </td>

                  <td style={td}>
                    {employee.is_active
                      ? "Active"
                      : "Inactive"}
                  </td>

                  <td style={td}>
                    {employee.claimed_user_id
                      ? "Created"
                      : "Not created"}
                  </td>

                  <td style={td}>
                    {employee.is_active ? (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => {
                          void deactivate(
                            employee
                          );
                        }}
                      >
                        Deactivate
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th:
React.CSSProperties = {
  textAlign: "left",
  padding: 10,
  borderBottom:
    "1px solid #ddd",
};

const td:
React.CSSProperties = {
  padding: 10,
  borderBottom:
    "1px solid #eee",
};
