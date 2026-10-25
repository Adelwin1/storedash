"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";

import LocationPicker from "@/components/LocationPicker";


type ReadinessCheck = {
  key: string;
  label: string;
  ok: boolean;
  detail: string;
};


type MissingSupplier = {
  id: number;
  name: string;
  location: string | null;
  reason: string;
};


type OrderReadiness = {
  order_id: number;

  ready: boolean;

  can_generate_price: boolean;

  stage: string;

  checks:
    ReadinessCheck[];

  customer: {
    id: number;
    name: string | null;
    address: string | null;
    location_confirmed: boolean;
  };

  missing_suppliers:
    MissingSupplier[];

  deliverable_item_count:
    number;

  issue_count:
    number;
};


export default function OrderPricingReadiness({
  orderId,
  refreshKey,
  onGenerate,
}: {
  orderId: number;

  refreshKey: string;

  onGenerate:
    () => Promise<void>;
}) {
  const [
    readiness,
    setReadiness,
  ] = useState<
    OrderReadiness | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    generating,
    setGenerating,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  const loadReadiness =
    useCallback(
      async () => {
        try {
          setLoading(true);

          const data =
            await api<
              OrderReadiness
            >(
              `/orders/${orderId}/readiness`
            );

          setReadiness(
            data
          );

          setError("");

        } catch (error) {
          setError(
            error instanceof Error
              ? error.message
              : "Could not check order readiness."
          );

        } finally {
          setLoading(false);
        }
      },
      [
        orderId,
      ]
    );


  useEffect(() => {
    loadReadiness();

  }, [
    loadReadiness,
    refreshKey,
  ]);


  async function generate() {
    try {
      setGenerating(
        true
      );

      setError("");

      await onGenerate();

      await loadReadiness();

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not generate final price."
      );

    } finally {
      setGenerating(
        false
      );
    }
  }


  if (loading && !readiness) {
    return (
      <div
        className="label"
        style={{
          marginTop: 16,
        }}
      >
        Checking order readiness...
      </div>
    );
  }


  if (!readiness) {
    return (
      <div
        className="error"
        style={{
          marginTop: 16,
        }}
      >
        {error ||
          "Could not check order readiness."}
      </div>
    );
  }


  return (
    <div
      style={{
        marginTop: 16,
      }}
    >
      <h3>
        Order Readiness
      </h3>


      <div
        style={{
          display: "grid",
          gap: 10,
          marginTop: 12,
        }}
      >
        {
          readiness.checks.map(
            (check) => (
              <div
                key={
                  check.key
                }
                style={{
                  display:
                    "flex",

                  gap: 10,

                  alignItems:
                    "flex-start",

                  padding:
                    "10px 0",

                  borderBottom:
                    "1px solid #f1f5f9",
                }}
              >
                <div
                  style={{
                    fontSize: 18,
                    lineHeight: 1,
                  }}
                >
                  {
                    check.ok
                      ? "✅"
                      : "❌"
                  }
                </div>

                <div>
                  <strong>
                    {
                      check.label
                    }
                  </strong>

                  <div
                    className="label"
                    style={{
                      marginTop: 3,
                    }}
                  >
                    {
                      check.detail
                    }
                  </div>
                </div>
              </div>
            )
          )
        }
      </div>


      {
        !readiness.customer
          .location_confirmed
        && (
          <div
            style={{
              marginTop: 20,
              paddingTop: 18,
              borderTop:
                "1px solid #e5e7eb",
            }}
          >
            <h3>
              Fix Customer Location
            </h3>

            <p className="label">
              Confirm the customer's
              delivery point before
              StoreDash calculates
              delivery pricing.
            </p>

            <LocationPicker
              entityType="business"
              entityId={
                readiness.customer.id
              }
              initialLocation={
                readiness.customer.address
              }
              onSaved={() => {
                loadReadiness();
              }}
            />
          </div>
        )
      }


      {
        readiness
          .missing_suppliers
          .length > 0
        && (
          <div
            style={{
              marginTop: 20,
              paddingTop: 18,
              borderTop:
                "1px solid #e5e7eb",
            }}
          >
            <h3>
              Fix Supplier Locations
            </h3>

            <p className="label">
              Confirm each pickup
              location used by this
              order.
            </p>

            {
              readiness
                .missing_suppliers
                .map(
                  (
                    supplier
                  ) => (
                    <div
                      key={
                        supplier.id
                      }
                      style={{
                        marginTop:
                          18,

                        paddingTop:
                          14,

                        borderTop:
                          "1px solid #f1f5f9",
                      }}
                    >
                      <strong>
                        {
                          supplier.name
                        }
                      </strong>

                      <LocationPicker
                        entityType="supplier"
                        entityId={
                          supplier.id
                        }
                        initialLocation={
                          supplier.location
                        }
                        onSaved={() => {
                          loadReadiness();
                        }}
                      />
                    </div>
                  )
                )
            }
          </div>
        )
      }


      {
        readiness.ready
        && readiness
          .can_generate_price
        && (
          <div
            className="notice"
            style={{
              marginTop: 20,
            }}
          >
            <strong>
              ✅ Ready for Final Price
            </strong>

            <div
              className="label"
              style={{
                marginTop: 5,
              }}
            >
              All sourcing,
              logistics and location
              requirements are complete.
            </div>


            <button
              className="btn"
              style={{
                marginTop: 14,
              }}
              disabled={
                generating
              }
              onClick={
                generate
              }
            >
              {
                generating
                  ? "Calculating..."
                  : "Generate Final Price"
              }
            </button>
          </div>
        )
      }


      {
        !readiness.ready
        && (
          <div
            className="error"
            style={{
              marginTop: 20,
            }}
          >
            Final pricing is blocked by{" "}
            {
              readiness.issue_count
            }{" "}
            requirement
            {
              readiness.issue_count
              === 1
                ? ""
                : "s"
            }.
          </div>
        )
      }


      {error && (
        <div
          className="error"
          style={{
            marginTop: 14,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
