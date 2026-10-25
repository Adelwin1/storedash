"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { api } from "@/lib/api";


type Order = {
  order_id: number;
  daily_number: number | null;
  customer_name: string | null;
  status: string;
  weight_kg: number;
  volume_l: number;
  delivery_fee: number;
  delivery_sequence: number | null;
};


type Stop = {
  sequence: number;
  stop_type: string;
  location_label: string | null;
  weight_delta_kg: number;
  volume_delta_l: number;
  load_weight_after_kg: number;
  load_volume_after_l: number;
  leg_distance_km: number;
  leg_minutes: number;
  status: string;
};


type Route = {
  batch_id: number;
  business_date: string;
  completed_at: string;
  status: string;
  order_count: number;
  pickup_count: number;
  delivery_count: number;
  distance_km: number;
  road_minutes: number;
  peak_weight_kg: number;
  peak_volume_l: number;
  delivery_revenue: number;
  driver_payout: number | null;
  contribution: number | null;
  orders: Order[];
  stops: Stop[];
};


type History = {
  driver: {
    id: number;
    name: string;
    phone: string;
    vehicle_type: string;
    vehicle_registration: string | null;
    current_area: string | null;
    is_available: boolean;
  };

  routes: Route[];
};


function money(
  value: number | null
) {
  return value == null
    ? "—"
    : `GH₵${value.toFixed(2)}`;
}


function pretty(
  value: string
) {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (x) => x.toUpperCase()
    );
}


function dayLabel(
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


export default function DriverHistoryPage() {

  const params =
    useParams();

  const id =
    Array.isArray(
      params.id
    )
      ? params.id[0]
      : params.id;


  const [
    history,
    setHistory,
  ] =
    useState<History | null>(
      null
    );


  const [
    error,
    setError,
  ] =
    useState("");


  useEffect(() => {

    if (!id) {
      return;
    }

    api<History>(
      `/drivers/${id}/delivery-history`
    )
      .then(
        setHistory
      )
      .catch(
        (err) =>
          setError(
            err instanceof Error
              ? err.message
              : "Could not load history."
          )
      );

  }, [id]);


  const grouped =
    useMemo(() => {

      const map =
        new Map<
          string,
          Route[]
        >();

      for (
        const route
        of history?.routes
        ?? []
      ) {

        const list =
          map.get(
            route.business_date
          )
          ?? [];

        list.push(
          route
        );

        map.set(
          route.business_date,
          list
        );
      }

      return Array.from(
        map.entries()
      );

    }, [history]);


  if (error) {

    return (
      <div className="card">
        {error}
      </div>
    );
  }


  if (!history) {

    return (
      <div className="card">
        Loading driver history...
      </div>
    );
  }


  return (
    <>

      <div className="header">

        <div>

          <h1>
            {history.driver.name}
          </h1>

          <p className="label">
            {history.driver.phone}
            {" · "}
            {history.driver.vehicle_type}
            {" · "}
            {
              history.driver.current_area
              ?? "No current area"
            }
          </p>

        </div>


        <Link
          href="/drivers"
          className="btn btn-secondary"
        >
          Drivers
        </Link>

      </div>


      {
        grouped.length === 0
          ? (
              <div className="card">
                No completed routes yet.
              </div>
            )
          : grouped.map(
              (
                [
                  day,
                  routes,
                ]
              ) => (

                <div
                  key={day}
                  style={{
                    marginBottom: 28,
                  }}
                >

                  <h2>
                    {dayLabel(day)}
                  </h2>


                  {
                    routes.map(
                      (route) => (

                        <div
                          className="card"
                          key={
                            route.batch_id
                          }
                          style={{
                            marginTop: 14,
                          }}
                        >

                          <h3>
                            Route #
                            {route.batch_id}
                          </h3>


                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns:
                                "repeat(auto-fit, minmax(150px, 1fr))",
                              gap: 14,
                              marginTop: 16,
                            }}
                          >

                            <div>
                              <div className="label">
                                Orders
                              </div>

                              <strong>
                                {route.order_count}
                              </strong>
                            </div>


                            <div>
                              <div className="label">
                                Distance
                              </div>

                              <strong>
                                {route.distance_km.toFixed(1)} km
                              </strong>
                            </div>


                            <div>
                              <div className="label">
                                Road time
                              </div>

                              <strong>
                                {route.road_minutes.toFixed(0)} min
                              </strong>
                            </div>


                            <div>
                              <div className="label">
                                Peak load
                              </div>

                              <strong>
                                {route.peak_weight_kg.toFixed(1)} kg
                              </strong>

                              <div className="label">
                                {route.peak_volume_l.toFixed(1)} L
                              </div>
                            </div>


                            <div>
                              <div className="label">
                                Driver payout
                              </div>

                              <strong>
                                {money(route.driver_payout)}
                              </strong>
                            </div>


                            <div>
                              <div className="label">
                                Delivery revenue
                              </div>

                              <strong>
                                {money(route.delivery_revenue)}
                              </strong>
                            </div>


                            <div>
                              <div className="label">
                                Contribution
                              </div>

                              <strong>
                                {money(route.contribution)}
                              </strong>
                            </div>

                          </div>


                          <h3
                            style={{
                              marginTop: 24,
                            }}
                          >
                            Orders
                          </h3>


                          <table className="table">

                            <thead>

                              <tr>
                                <th>Order</th>
                                <th>Customer</th>
                                <th>Load</th>
                                <th>Delivery Fee</th>
                                <th></th>
                              </tr>

                            </thead>


                            <tbody>

                              {
                                route.orders.map(
                                  (order) => (

                                    <tr
                                      key={
                                        order.order_id
                                      }
                                    >

                                      <td>
                                        #
                                        {
                                          order.daily_number
                                          ??
                                          order.order_id
                                        }
                                      </td>

                                      <td>
                                        {
                                          order.customer_name
                                          ??
                                          "—"
                                        }
                                      </td>

                                      <td>
                                        {
                                          order.weight_kg.toFixed(1)
                                        } kg
                                        {" / "}
                                        {
                                          order.volume_l.toFixed(1)
                                        } L
                                      </td>

                                      <td>
                                        {
                                          money(
                                            order.delivery_fee
                                          )
                                        }
                                      </td>

                                      <td>
                                        <Link
                                          href={
                                            `/orders/${order.order_id}`
                                          }
                                          className="text-link"
                                        >
                                          Full Order →
                                        </Link>
                                      </td>

                                    </tr>

                                  )
                                )
                              }

                            </tbody>

                          </table>


                          <h3
                            style={{
                              marginTop: 24,
                            }}
                          >
                            Route Stops
                          </h3>


                          <table className="table">

                            <thead>

                              <tr>
                                <th>#</th>
                                <th>Type</th>
                                <th>Location</th>
                                <th>Load Change</th>
                                <th>Load After</th>
                                <th>Leg</th>
                              </tr>

                            </thead>


                            <tbody>

                              {
                                route.stops.map(
                                  (stop) => (

                                    <tr
                                      key={
                                        stop.sequence
                                      }
                                    >

                                      <td>
                                        {stop.sequence}
                                      </td>

                                      <td>
                                        {
                                          pretty(
                                            stop.stop_type
                                          )
                                        }
                                      </td>

                                      <td>
                                        {
                                          stop.location_label
                                          ?? "—"
                                        }
                                      </td>

                                      <td>
                                        {
                                          stop.weight_delta_kg.toFixed(1)
                                        } kg
                                        <br />
                                        {
                                          stop.volume_delta_l.toFixed(1)
                                        } L
                                      </td>

                                      <td>
                                        {
                                          stop.load_weight_after_kg.toFixed(1)
                                        } kg
                                        <br />
                                        {
                                          stop.load_volume_after_l.toFixed(1)
                                        } L
                                      </td>

                                      <td>
                                        {
                                          stop.leg_distance_km.toFixed(1)
                                        } km
                                        <br />
                                        {
                                          stop.leg_minutes.toFixed(0)
                                        } min
                                      </td>

                                    </tr>

                                  )
                                )
                              }

                            </tbody>

                          </table>

                        </div>

                      )
                    )
                  }

                </div>

              )
            )
      }

    </>
  );
}
