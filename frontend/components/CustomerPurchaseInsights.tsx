"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type FrequentProduct = {
  name: string;

  purchase_count: number;

  total_quantity: number;

  average_quantity: number;

  last_quantity: number;

  unit: string;

  last_purchase_at: string;

  last_order_id: number;

  last_order_number: string;
};


type PurchaseSummary = {
  business_id: number;

  completed_order_count: number;

  unique_product_count: number;

  frequent_products:
    FrequentProduct[];
};


export default function CustomerPurchaseInsights({
  businessId,
}: {
  businessId: number;
}) {
  const [
    summary,
    setSummary,
  ] = useState<
    PurchaseSummary | null
  >(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {
    async function load() {
      try {
        const data =
          await api<
            PurchaseSummary
          >(
            `/businesses/${businessId}/purchase-summary`
          );

        setSummary(
          data
        );

      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Could not load purchase history."
        );

      } finally {
        setLoading(
          false
        );
      }
    }


    load();

  }, [businessId]);


  if (loading) {
    return (
      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        Loading purchase patterns...
      </div>
    );
  }


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
            Frequently Bought
          </h2>

          <p className="label">
            Based only on completed
            StoreDash transactions.
          </p>
        </div>


        <div>
          <strong>
            {
              summary.completed_order_count
            }
          </strong>

          <span className="label">
            {" "}
            completed orders
          </span>
        </div>
      </div>


      {summary.frequent_products.length ===
      0 ? (
        <div className="empty-state">
          No completed purchase history
          yet.
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>
                Product
              </th>

              <th>
                Bought
              </th>

              <th>
                Total Qty
              </th>

              <th>
                Average
              </th>

              <th>
                Last Qty
              </th>

              <th>
                Last Purchased
              </th>

              <th>
                Last Order
              </th>
            </tr>
          </thead>


          <tbody>
            {summary.frequent_products.map(
              (product) => (
                <tr
                  key={
                    product.name
                  }
                >
                  <td>
                    <strong>
                      {
                        product.name
                      }
                    </strong>
                  </td>


                  <td>
                    {
                      product.purchase_count
                    }
                    ×
                  </td>


                  <td>
                    {
                      product.total_quantity
                    }{" "}
                    {
                      product.unit
                    }
                  </td>


                  <td>
                    {
                      product.average_quantity
                    }{" "}
                    {
                      product.unit
                    }
                  </td>


                  <td>
                    <strong>
                      {
                        product.last_quantity
                      }{" "}
                      {
                        product.unit
                      }
                    </strong>
                  </td>


                  <td>
                    {new Date(
                      product.last_purchase_at
                    ).toLocaleDateString()}
                  </td>


                  <td>
                    <Link
                      href={
                        `/orders/${product.last_order_id}`
                      }
                      className="text-link"
                    >
                      {
                        product.last_order_number
                      }
                    </Link>
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
