"use client";

import {
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type LoadSummary = {
  order_id: number;

  total_load_units: number;

  load_class: string;

  unclassified_items:
    string[];

  classification_complete:
    boolean;
};


export default function OrderLoadSummary({
  orderId,
}: {
  orderId: number;
}) {
  const [
    summary,
    setSummary,
  ] = useState<
    LoadSummary | null
  >(null);


  const [
    error,
    setError,
  ] = useState("");


  async function load() {
    try {
      const data =
        await api<
          LoadSummary
        >(
          `/orders/${orderId}/load-summary`
        );


      setSummary(
        data
      );

      setError(
        ""
      );


    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not calculate order load."
      );
    }
  }


  useEffect(() => {
    load();


    function logisticsUpdated(
      event: Event
    ) {
      const custom =
        event as CustomEvent<{
          orderId: number;
        }>;


      if (
        custom.detail?.orderId
        === orderId
      ) {
        load();
      }
    }


    window.addEventListener(
      "storedash:logistics-updated",
      logisticsUpdated
    );


    return () => {
      window.removeEventListener(
        "storedash:logistics-updated",
        logisticsUpdated
      );
    };

  }, [orderId]);


  if (error) {
    return (
      <div
        className="notice"
        style={{
          marginTop: 20,
        }}
      >
        {error}
      </div>
    );
  }


  if (!summary) {
    return null;
  }


  return (
    <div
      className="card"
      style={{
        marginTop: 20,
      }}
    >
      <div className="header">
        <div>
          <h2>
            Delivery Load
          </h2>

          <p className="label">
            Calculated from all
            deliverable order items.
          </p>
        </div>


        <div
          style={{
            textAlign: "right",
          }}
        >
          <div className="label">
            Load class
          </div>

          <strong
            style={{
              fontSize: 22,
            }}
          >
            {summary.load_class.toUpperCase()}
          </strong>
        </div>
      </div>


      <div className="grid grid-2">
        <div>
          <div className="label">
            Total load units
          </div>

          <div className="metric">
            {
              summary.total_load_units
            }
          </div>
        </div>


        <div>
          <div className="label">
            Classification
          </div>

          <div
            style={{
              marginTop: 7,
            }}
          >
            {summary.classification_complete ? (
              <span className="badge">
                COMPLETE
              </span>
            ) : (
              <span className="badge">
                INCOMPLETE
              </span>
            )}
          </div>
        </div>
      </div>


      {!summary.classification_complete && (
        <div
          className="notice"
          style={{
            marginTop: 14,
          }}
        >
          Classify:{" "}
          {
            summary.unclassified_items.join(
              ", "
            )
          }
        </div>
      )}
    </div>
  );
}
