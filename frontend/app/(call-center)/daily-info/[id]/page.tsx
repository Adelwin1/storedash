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

import type {
  Business,
  Order,
} from "@/lib/types";


type DailyOrder = Order & {
  operating_day_id: number | null;
  daily_number: number | null;
};


type DaySummary = {
  id: number;
  business_date: string;
  opened_at: string;
  closed_at: string | null;
  is_closed: boolean;
  closed_by_id: number | null;
  notes: string | null;

  total_orders: number;
  draft_orders: number;
  active_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  failed_orders: number;

  goods_total: number | string;
  delivery_fee_total: number | string;
  service_fee_total: number | string;
  final_total: number | string;
};


export default function DailyReportPage() {
  const params =
    useParams<{
      id: string;
    }>();


  const [day, setDay] =
    useState<DaySummary | null>(
      null
    );

  const [orders, setOrders] =
    useState<DailyOrder[]>([]);

  const [customers, setCustomers] =
    useState<Business[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {
    async function loadReport() {
      try {
        const [
          dayData,
          orderData,
          customerData,
        ] = await Promise.all([
          api<DaySummary>(
            `/operating-days/${params.id}`
          ),

          api<DailyOrder[]>(
            `/orders?operating_day_id=${params.id}`
          ),

          api<Business[]>(
            "/businesses?limit=200"
          ),
        ]);


        setDay(
          dayData
        );

        setOrders(
          orderData.sort(
            (a, b) =>
              (a.daily_number ?? 0) -
              (b.daily_number ?? 0)
          )
        );

        setCustomers(
          customerData
        );

      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Could not load daily report."
        );

      } finally {
        setLoading(
          false
        );
      }
    }


    if (params.id) {
      loadReport();
    }

  }, [params.id]);


  function customerName(
    businessId: number
  ) {
    const customer =
      customers.find(
        (item) =>
          item.id ===
          businessId
      );

    return customer
      ? customer.business_name
      : `Customer ID ${businessId}`;
  }


  if (loading) {
    return (
      <div className="card">
        Loading daily report...
      </div>
    );
  }


  if (!day) {
    return (
      <div className="card">
        {error ||
          "Operating day not found."}
      </div>
    );
  }


  return (
    <>
      <div className="header">
        <div>
          <h1>
            {
              day.business_date
            }
          </h1>

          <p className="label">
            StoreDash Daily Report
          </p>
        </div>


        <Link
          href="/daily-info"
          className="btn btn-secondary"
        >
          Back
        </Link>
      </div>


      {error && (
        <div className="notice">
          {error}
        </div>
      )}


      <div className="grid grid-3">
        <div className="card">
          <div className="label">
            Total Orders
          </div>

          <div className="metric">
            {
              day.total_orders
            }
          </div>
        </div>


        <div className="card">
          <div className="label">
            Completed
          </div>

          <div className="metric">
            {
              day.completed_orders
            }
          </div>
        </div>


        <div className="card">
          <div className="label">
            Failed / Cancelled
          </div>

          <div className="metric">
            {
              day.failed_orders +
              day.cancelled_orders
            }
          </div>
        </div>
      </div>


      <div
        className="grid grid-3"
        style={{
          marginTop: 20,
        }}
      >
        <div className="card">
          <div className="label">
            Goods
          </div>

          <div className="metric">
            GH₵
            {
              Number(
                day.goods_total
              ).toFixed(2)
            }
          </div>
        </div>


        <div className="card">
          <div className="label">
            Delivery Fees
          </div>

          <div className="metric">
            GH₵
            {
              Number(
                day.delivery_fee_total
              ).toFixed(2)
            }
          </div>
        </div>


        <div className="card">
          <div className="label">
            Service Fees
          </div>

          <div className="metric">
            GH₵
            {
              Number(
                day.service_fee_total
              ).toFixed(2)
            }
          </div>
        </div>
      </div>


      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <h2>
          Orders
        </h2>


        {orders.length === 0 ? (
          <div className="empty-state">
            No orders.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>
                  #
                </th>

                <th>
                  Internal #
                </th>

                <th>
                  Customer
                </th>

                <th>
                  Items
                </th>

                <th>
                  Status
                </th>

                <th></th>
              </tr>
            </thead>

            <tbody>
              {orders.map(
                (order) => (
                  <tr
                    key={
                      order.id
                    }
                  >
                    <td>
                      <strong>
                        #
                        {
                          order.daily_number
                        }
                      </strong>
                    </td>

                    <td>
                      {
                        order.order_number
                      }
                    </td>

                    <td>
                      {
                        customerName(
                          order.business_id
                        )
                      }
                    </td>

                    <td>
                      {order.items
                        .map(
                          (item) =>
                            `${item.name} ×${item.requested_quantity}`
                        )
                        .join(", ")}
                    </td>

                    <td>
                      <span className="badge">
                        {order.status
                          .replaceAll(
                            "_",
                            " "
                          )
                          .toUpperCase()}
                      </span>
                    </td>

                    <td>
                      <Link
                        href={
                          `/orders/${order.id}`
                        }
                        className="btn btn-secondary"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
