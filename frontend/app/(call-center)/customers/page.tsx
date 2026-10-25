"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import type { Business } from "@/lib/types";

export default function CustomersPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Business[]>([]);
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);
  const [searching, setSearching] = useState(false);

  async function searchCustomers() {
    setSearching(true);
    setMessage("");

    try {
      const data = await api<Business[]>(
        `/businesses?q=${encodeURIComponent(query.trim())}`
      );

      setResults(data);

      setMessage(
        data.length
          ? ""
          : "No customer found — register them while they are on the phone."
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Search failed"
      );
    } finally {
      setSearching(false);
    }
  }

  async function createCustomer(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    /*
      Save the form element BEFORE the await.

      React's event.currentTarget may become null
      after the asynchronous request finishes.
    */
    const formElement = event.currentTarget;

    const form = new FormData(formElement);

    const payload = Object.fromEntries(
      form.entries()
    );

    setCreating(true);
    setMessage("");

    try {
      const created = await api<Business>(
        "/businesses",
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      );

      setMessage(
        `Created ${created.business_name}. StoreDash customer #${created.customer_number} is ready.`
      );

      setResults([created]);

      /*
        Reset the saved form element,
        not event.currentTarget.
      */
      formElement.reset();

    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create customer"
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
            Search by customer number, owner name,
            business name or phone. Open a customer
            to see their full history.
          </p>
        </div>
      </div>

      {/* CUSTOMER SEARCH */}

      <div className="card">
        <h2>Find customer</h2>

        <div className="toolbar">
          <input
            className="input"
            style={{
              maxWidth: 560,
            }}
            value={query}
            onChange={(event) =>
              setQuery(event.target.value)
            }
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                searchCustomers();
              }
            }}
            placeholder="Customer #000, name, business or phone"
          />

          <button
            className="btn"
            type="button"
            onClick={searchCustomers}
            disabled={searching}
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
                <th>#</th>
                <th>Business</th>
                <th>Owner</th>
                <th>Phone</th>
                <th>Location</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {results.map((business) => (
                <tr key={business.id}>
                  <td>
                    <span className="number-badge">
                      {business.customer_number}
                    </span>
                  </td>

                  <td>
                    {business.business_name}
                  </td>

                  <td>
                    {business.owner_name}
                  </td>

                  <td>
                    {business.phone}
                  </td>

                  <td>
                    {business.address ||
                      business.landmark ||
                      "—"}
                  </td>

                  <td>
                    <Link
                      className="text-link"
                      href={`/customers/${business.id}`}
                    >
                      View profile →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* REGISTER NEW CUSTOMER */}

      <div
        className="card"
        style={{
          marginTop: 18,
        }}
      >
        <h2>+ Register new caller</h2>

        <p className="label">
          The customer number is generated
          automatically, starting from 000.
        </p>

        <form
          onSubmit={createCustomer}
          className="form-grid"
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
            Alternative phone

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
              placeholder="Kiosk, restaurant, mini-mart..."
            />
          </label>

          <label>
            Area / address

            <input
              className="input"
              name="address"
            />
          </label>

          <label className="full">
            Landmark

            <input
              className="input"
              name="landmark"
            />
          </label>

          <label className="full">
            Delivery instructions

            <textarea
              className="textarea"
              name="delivery_instructions"
              placeholder="Gate, landmark, delivery notes..."
            />
          </label>

          <div className="full">
            <button
              className="btn"
              type="submit"
              disabled={creating}
            >
              {creating
                ? "Saving..."
                : "Save customer"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}