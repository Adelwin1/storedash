"use client";

import Link from "next/link";
import {
  FormEvent,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { Business } from "@/lib/types";

export default function FieldCustomersPage() {
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [results, setResults] =
    useState<Business[]>([]);
  const [message, setMessage] =
    useState("");
  const [searching, setSearching] =
    useState(false);
  const [creating, setCreating] =
    useState(false);

  async function searchCustomers() {
    setSearching(true);
    setMessage("");

    try {
      const data = await api<Business[]>(
        `/businesses?q=${encodeURIComponent(
          query.trim()
        )}`
      );

      setResults(data);

      if (data.length === 0) {
        setMessage(
          "No customer found."
        );
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Search failed."
      );
    } finally {
      setSearching(false);
    }
  }

  async function createCustomer(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const formElement =
      event.currentTarget;

    const form =
      new FormData(formElement);

    const payload =
      Object.fromEntries(
        form.entries()
      );

    setCreating(true);
    setMessage("");

    try {
      const created =
        await api<Business>(
          "/businesses",
          {
            method: "POST",
            body: JSON.stringify(
              payload
            ),
          }
        );

      router.push(
        `/field/customers/${created.id}`
      );

      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create customer."
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <>
      <div className="header">
        <div>
          <h1>Customers</h1>

          <p className="label">
            Find an existing customer by
            StoreDash code, name, business
            name or phone, or register a
            new customer.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>Find customer</h2>

        <div className="toolbar">
          <input
            className="input"
            style={{
              maxWidth: 560,
            }}
            value={query}
            placeholder="A8, name, business or phone"
            onChange={(event) =>
              setQuery(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key === "Enter"
              ) {
                void searchCustomers();
              }
            }}
          />

          <button
            className="btn"
            type="button"
            disabled={searching}
            onClick={() =>
              void searchCustomers()
            }
          >
            {searching
              ? "Searching..."
              : "Search"}
          </button>
        </div>

        {message && (
          <div className="notice">
            {message}
          </div>
        )}

        {results.length > 0 && (
          <table
            className="table"
            style={{
              marginTop: 12,
            }}
          >
            <thead>
              <tr>
                <th>Code</th>
                <th>Business</th>
                <th>Owner</th>
                <th>Phone</th>
                <th>Location</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {results.map(
                (business) => (
                  <tr key={business.id}>
                    <td>
                      <span className="number-badge">
                        {
                          business.customer_number
                        }
                      </span>
                    </td>

                    <td>
                      {
                        business.business_name
                      }
                    </td>

                    <td>
                      {
                        business.owner_name
                      }
                    </td>

                    <td>
                      {business.phone}
                    </td>

                    <td>
                      {business.address
                        || business.landmark
                        || "Not saved"}
                    </td>

                    <td>
                      <Link
                        className="text-link"
                        href={`/field/customers/${business.id}`}
                      >
                        View profile →
                      </Link>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </div>

      <div
        className="card"
        style={{
          marginTop: 18,
        }}
      >
        <h2>Add Customer</h2>

        <p className="label">
          StoreDash generates the customer
          code automatically. After the
          customer is created, save their
          exact delivery location.
        </p>

        <form
          className="form-grid"
          onSubmit={createCustomer}
        >
          <label>
            Customer / owner name

            <input
              className="input"
              name="owner_name"
              required
            />
          </label>

          <label>
            Business name

            <input
              className="input"
              name="business_name"
              required
            />
          </label>

          <label>
            Phone

            <input
              className="input"
              name="phone"
              required
            />
          </label>

          <label>
            Alternate phone

            <input
              className="input"
              name="alternate_phone"
            />
          </label>

          <label>
            Business type

            <input
              className="input"
              name="business_type"
            />
          </label>

          <label>
            Landmark

            <input
              className="input"
              name="landmark"
            />
          </label>

          <label>
            Delivery instructions

            <input
              className="input"
              name="delivery_instructions"
            />
          </label>

          <div>
            <button
              className="btn"
              type="submit"
              disabled={creating}
            >
              {creating
                ? "Creating..."
                : "Create Customer"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
