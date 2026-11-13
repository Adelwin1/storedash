"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
} from "react";
import {
  useParams,
} from "next/navigation";

import { api } from "@/lib/api";
import LocationPicker
  from "@/components/LocationPicker";
import type {
  Business,
} from "@/lib/types";

export default function FieldCustomerProfilePage() {
  const params =
    useParams<{
      id: string;
    }>();

  const [customer, setCustomer] =
    useState<Business | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    async function loadCustomer() {
      try {
        setLoading(true);
        setError("");

        const data =
          await api<Business>(
            `/businesses/${params.id}`
          );

        setCustomer(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Could not load customer."
        );
      } finally {
        setLoading(false);
      }
    }

    void loadCustomer();
  }, [params.id]);

  if (loading) {
    return (
      <div className="card">
        Loading customer...
      </div>
    );
  }

  if (
    error
    || !customer
  ) {
    return (
      <div className="card">
        {error || "Customer not found."}
      </div>
    );
  }

  return (
    <>
      <div className="header">
        <div>
          <Link
            className="text-link"
            href="/field/customers"
          >
            ← Customers
          </Link>

          <h1
            style={{
              marginTop: 10,
            }}
          >
            {customer.owner_name}
          </h1>

          <p className="label">
            Verify the customer details and
            save the exact delivery location.
          </p>
        </div>

        <span className="number-badge">
          {customer.customer_number}
        </span>
      </div>

      <div className="card">
        <h2>Customer Details</h2>

        <div
          style={{
            display: "grid",
            gap: 14,
            gridTemplateColumns:
              "repeat(auto-fit, minmax(200px, 1fr))",
            marginTop: 16,
          }}
        >
          <div>
            <div className="label">
              StoreDash Code
            </div>

            <strong>
              {customer.customer_number}
            </strong>
          </div>

          <div>
            <div className="label">
              Owner
            </div>

            <strong>
              {customer.owner_name}
            </strong>
          </div>

          <div>
            <div className="label">
              Business
            </div>

            <strong>
              {customer.business_name}
            </strong>
          </div>

          <div>
            <div className="label">
              Phone
            </div>

            <strong>
              {customer.phone}
            </strong>
          </div>

          <div>
            <div className="label">
              Alternate Phone
            </div>

            <strong>
              {customer.alternate_phone
                || "—"}
            </strong>
          </div>

          <div>
            <div className="label">
              Business Type
            </div>

            <strong>
              {customer.business_type
                || "—"}
            </strong>
          </div>

          <div>
            <div className="label">
              Landmark
            </div>

            <strong>
              {customer.landmark
                || "—"}
            </strong>
          </div>

          <div>
            <div className="label">
              Saved Location
            </div>

            <strong>
              {customer.address
                || "Not saved yet"}
            </strong>
          </div>
        </div>
      </div>

      <div
        className="card"
        style={{
          marginTop: 18,
        }}
      >
        <LocationPicker
          entityType="business"
          entityId={customer.id}
          initialLocation={
            customer.address
          }
          onSaved={(address) => {
            setCustomer({
              ...customer,
              address,
            });
          }}
        />
      </div>

      <div
        className="notice"
        style={{
          marginTop: 18,
        }}
      >
        This field workspace does not
        contain orders, payments, payouts
        or dispatch controls.
      </div>
    </>
  );
}
