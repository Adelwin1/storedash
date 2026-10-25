"use client";

import Link from "next/link";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { api } from "@/lib/api";

type Order = {
  id: number;
  operating_day_id: number | null;
  daily_number: number | null;
  business_id: number;
  status: string;
  final_total?: string | number | null;
};

type Business = {
  id: number;
  name: string;
};

type OperatingDay = {
  id: number;
  business_date: string;
  is_closed: boolean;
};

function formatDate(
  value: string
) {
  return new Date(
    `${value}T12:00:00`
  ).toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "long",
      day: "numeric",
    }
  );
}

function formatStatus(
  value: string
) {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase()
    );
}

export default function OrdersPage() {

  const [orders, setOrders] =
    useState<Order[]>([]);

  const [days, setDays] =
    useState<OperatingDay[]>([]);

  const [businesses, setBusinesses] =
    useState<Business[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {

    async function load() {

      try {

        const [
          orderData,
          dayData,
          businessData,
        ] = await Promise.all([
          api<Order[]>("/orders"),
          api<OperatingDay[]>(
            "/operating-days"
          ),
          api<Business[]>(
            "/businesses?limit=200"
          ),
        ]);

        setOrders(orderData);
        setDays(dayData);
        setBusinesses(
          businessData
        );

      } catch (err) {

        setError(
          err instanceof Error
            ? err.message
            : "Could not load orders."
        );

      } finally {

        setLoading(false);
      }
    }

    void load();

  }, []);


  const businessNames =
    useMemo(() => {

      const map =
        new Map<number, string>();

      businesses.forEach(
        (business) => {

          map.set(
            business.id,
            business.name
          );
        }
      );

      return map;

    }, [businesses]);


  const visibleDays =
    useMemo(() => {

      return [...days]
        .sort(
          (a, b) =>
            b.business_date.localeCompare(
              a.business_date
            )
        )
        .slice(0, 7);

    }, [days]);


  if (loading) {

    return (
      <div className="card">
        Loading orders...
      </div>
    );
  }


  return (
    <>
      <div className="header">

        <div>
          <h1>
            Orders
          </h1>

          <p className="label">
            Latest 7 operating days.
            Older orders remain stored
            in StoreDash.
          </p>
        </div>

        <Link
          href="/orders/new"
          className="btn"
        >
          New Order
        </Link>

      </div>


      {error && (
        <div className="notice">
          {error}
        </div>
      )}


      {visibleDays.length === 0 ? (

        <div className="card">
          No operating days yet.
        </div>

      ) : (

        visibleDays.map(
          (day) => {

            const dayOrders =
              orders
                .filter(
                  (order) =>
                    order.operating_day_id
                    ===
                    day.id
                )
                .sort(
                  (a, b) =>
                    (
                      a.daily_number
                      ?? 999999
                    )
                    -
                    (
                      b.daily_number
                      ?? 999999
                    )
                );


            return (
              <div
                className="card"
                key={day.id}
                style={{
                  marginBottom: 20,
                }}
              >

                <h2>
                  {formatDate(
                    day.business_date
                  )}
                </h2>

                <p className="label">
                  {day.is_closed
                    ? "Closed operating day"
                    : "Current operating day"}
                </p>


                {dayOrders.length === 0 ? (

                  <div className="empty-state">
                    No orders.
                  </div>

                ) : (

                  <table className="table">

                    <thead>
                      <tr>
                        <th>
                          Order
                        </th>

                        <th>
                          Customer
                        </th>

                        <th>
                          Status
                        </th>

                        <th>
                          Total
                        </th>

                        <th>
                        </th>
                      </tr>
                    </thead>


                    <tbody>

                      {dayOrders.map(
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
                                  ?? order.id
                                }
                              </strong>
                            </td>

                            <td>
                              {
                                businessNames.get(
                                  order.business_id
                                )
                                ??
                                `Customer ${order.business_id}`
                              }
                            </td>

                            <td>
                              {formatStatus(
                                order.status
                              )}
                            </td>

                            <td>
                              {
                                order.final_total
                                != null
                                  ? `GH₵${Number(
                                      order.final_total
                                    ).toFixed(2)}`
                                  : "—"
                              }
                            </td>

                            <td>
                              <Link
                                href={
                                  `/orders/${order.id}`
                                }
                                className="text-link"
                              >
                                View →
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
        )
      )}
    </>
  );
}
