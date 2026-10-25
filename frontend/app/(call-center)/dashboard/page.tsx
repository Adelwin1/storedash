"use client";

import Link from "next/link";

import {
  ShoppingBag,
  Activity,
  CircleCheckBig,
  UsersRound,
  RefreshCw,
  CalendarDays,
  ArrowRight,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { api } from "@/lib/api";

import type {
  Business,
  Order,
} from "@/lib/types";


type DashboardOrder = Order & {
  operating_day_id: number | null;
  daily_number: number | null;
};


type OperatingDay = {
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


const preFinalStatuses = [
  "draft",
  "sourcing",
  "quote_ready",
  "awaiting_buyer_approval",
];

const finishedStatuses = [
  "completed",
  "cancelled",
  "failed",
];


export default function DashboardPage() {
  const [orders, setOrders] =
    useState<DashboardOrder[]>([]);

  const [customers, setCustomers] =
    useState<Business[]>([]);

  const [operatingDay, setOperatingDay] =
    useState<OperatingDay | null>(null);

  const [search, setSearch] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [closing, setClosing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");


  async function loadDashboard(
    showLoading = false
  ) {
    try {
      if (showLoading) {
        setLoading(true);
      }

      const [
        orderData,
        customerData,
        dayData,
      ] = await Promise.all([
        api<DashboardOrder[]>(
          "/orders"
        ),

        api<Business[]>(
          "/businesses?limit=200"
        ),

        api<OperatingDay | null>(
          "/operating-days/current"
        ),
      ]);


      setOrders(
        orderData
      );

      setCustomers(
        customerData
      );

      setOperatingDay(
        dayData
      );

      setError("");

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not load dashboard."
      );

    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }


  useEffect(() => {
    void loadDashboard(true);

    const handleFocus = () => {
      void loadDashboard();
    };

    const handleVisibility = () => {
      if (
        document.visibilityState
        ===
        "visible"
      ) {
        void loadDashboard();
      }
    };

    const interval = window.setInterval(
      () => {
        void loadDashboard();
      },
      5000
    );

    window.addEventListener(
      "focus",
      handleFocus
    );

    document.addEventListener(
      "visibilitychange",
      handleVisibility
    );

    return () => {
      window.clearInterval(
        interval
      );

      window.removeEventListener(
        "focus",
        handleFocus
      );

      document.removeEventListener(
        "visibilitychange",
        handleVisibility
      );
    };
  }, []);


  const currentDayOrders =
    useMemo(() => {
      if (!operatingDay) {
        return [];
      }

      return orders.filter(
        (order) =>
          order.operating_day_id ===
          operatingDay.id
      );

    }, [
      orders,
      operatingDay,
    ]);


  const draftOrders =
    useMemo(() => {
      return currentDayOrders.filter(
        (order) =>
          preFinalStatuses.includes(
            order.status
          )
      );

    }, [
      currentDayOrders,
    ]);


  const allActiveOrders =
    useMemo(() => {
      return orders.filter(
        (order) =>
          !preFinalStatuses.includes(
            order.status
          ) &&
          !finishedStatuses.includes(
            order.status
          )
      );

    }, [
      orders,
    ]);


  const currentDayPastOrders =
    useMemo(() => {
      return currentDayOrders.filter(
        (order) =>
          finishedStatuses.includes(
            order.status
          )
      );

    }, [
      currentDayOrders,
    ]);


  function customerForOrder(
    businessId: number
  ) {
    return customers.find(
      (customer) =>
        customer.id ===
        businessId
    );
  }


  function matchesDailyNumber(
    order: DashboardOrder
  ) {
    const query =
      search.trim();

    if (!query) {
      return true;
    }

    if (
      order.operating_day_id !==
      operatingDay?.id
    ) {
      return false;
    }

    return (
      String(
        order.daily_number ?? ""
      ) === query
    );
  }


  const visibleDrafts =
    draftOrders.filter(
      matchesDailyNumber
    );


  const visibleActive =
    allActiveOrders.filter(
      (order) => {
        if (!search.trim()) {
          return true;
        }

        return matchesDailyNumber(
          order
        );
      }
    );


  const visiblePast =
    currentDayPastOrders.filter(
      matchesDailyNumber
    );


  async function closeDay() {
    const confirmed =
      window.confirm(
        "Close today's StoreDash operating day? You cannot add more orders after the day is closed."
      );

    if (!confirmed) {
      return;
    }


    try {
      setClosing(true);
      setError("");
      setMessage("");


      const result =
        await api<OperatingDay>(
          "/operating-days/current/close",
          {
            method: "POST",
          }
        );


      setOperatingDay(
        result
      );


      setMessage(
        `Operating day ${result.business_date} closed successfully.`
      );


      await loadDashboard();

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not close operating day."
      );

    } finally {
      setClosing(false);
    }
  }


  function renderOrders(
    sectionOrders: DashboardOrder[]
  ) {
    if (
      sectionOrders.length === 0
    ) {
      return (
        <div className="empty-state">
          No orders here.
        </div>
      );
    }


    return (
      <table className="table">
        <thead>
          <tr>
            <th>
              Day #
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

            <th>
              Day
            </th>

            <th></th>
          </tr>
        </thead>

        <tbody>
          {sectionOrders.map(
            (order) => {
              const customer =
                customerForOrder(
                  order.business_id
                );


              const isCarryover =
                operatingDay &&
                order.operating_day_id !==
                  operatingDay.id;


              return (
                <tr
                  key={
                    order.id
                  }
                >
                  <td>
                    {order.daily_number ? (
                      <strong
                        style={{
                          fontSize: 18,
                        }}
                      >
                        #
                        {
                          order.daily_number
                        }
                      </strong>
                    ) : (
                      "—"
                    )}
                  </td>


                  <td>
                    {
                      order.order_number
                    }
                  </td>


                  <td>
                    {customer ? (
                      <>
                        <strong>
                          {
                            customer.business_name
                          }
                        </strong>

                        <div className="label">
                          Customer #
                          {
                            customer.customer_number
                          }
                        </div>
                      </>
                    ) : (
                      `Customer ID ${order.business_id}`
                    )}
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
                    {isCarryover
                      ? "Carryover"
                      : operatingDay
                        ? "Today"
                        : "Previous"}
                  </td>


                  <td>
                    <Link
                      className="btn btn-secondary"
                      href={
                        `/orders/${order.id}`
                      }
                    >
                      Open
                    </Link>
                  </td>
                </tr>
              );
            }
          )}
        </tbody>
      </table>
    );
  }


  if (loading) {
    return (
      <div className="card">
        Loading StoreDash dashboard...
      </div>
    );
  }


  return (
    <>
      <section className="sd-hero">
        <div className="sd-hero-copy">
          <div className="sd-hero-kicker">
            StoreDash Operations
          </div>

          <h1>
            Source. Dispatch.
            <span>
              {" "}Deliver.
            </span>
          </h1>

          <p>
            Run today&apos;s local commerce
            from one place.
          </p>

          <div className="sd-hero-actions">
            <Link
              href="/orders/new"
              className="sd-primary-action"
            >
              New Order
              <ArrowRight size={17} />
            </Link>

            <Link
              href="/daily-info"
              className="sd-secondary-action"
            >
              <CalendarDays size={17} />
              Daily Info
            </Link>

            <button
              type="button"
              className="sd-secondary-action"
              onClick={() => {
                void loadDashboard();
              }}
            >
              <RefreshCw size={17} />
              Refresh
            </button>
          </div>
        </div>


        <div className="sd-hero-art">
          <div className="sd-yellow-blob" />

          <div className="sd-red-bubble">
            Local stores.
            <br />
            Real impact.
          </div>

          <div className="sd-delivery-visual">
            <div className="sd-visual-head" />

            <div className="sd-visual-body">
              <div className="sd-visual-logo">
                S
              </div>
            </div>

            <div className="sd-box-visual">
              <span />
              <span />
            </div>
          </div>
        </div>
      </section>


      {error && (
        <div
          className="notice"
          style={{
            marginBottom: 18,
          }}
        >
          {error}
        </div>
      )}


      {message && (
        <div
          className="notice"
          style={{
            marginBottom: 18,
          }}
        >
          {message}
        </div>
      )}


      <section className="sd-day-strip">
        <div>
          <span className="sd-day-label">
            Operating Day
          </span>

          <strong>
            {operatingDay
              ? operatingDay.business_date
              : "Not opened yet"}
          </strong>
        </div>

        <span
          className={
            operatingDay?.is_closed
              ? "sd-day-state sd-day-closed"
              : "sd-day-state sd-day-open"
          }
        >
          {operatingDay
            ? operatingDay.is_closed
              ? "Closed"
              : "Open"
            : "Waiting"}
        </span>

        {operatingDay &&
          !operatingDay.is_closed && (
            <button
              className="sd-close-day"
              disabled={closing}
              onClick={closeDay}
            >
              {closing
                ? "Closing..."
                : "Close Day"}
            </button>
          )}
      </section>


      <section className="sd-metric-grid">
        <div className="sd-metric-card sd-metric-red">
          <div className="sd-metric-icon">
            <ShoppingBag size={22} />
          </div>

          <div className="sd-metric-copy">
            <span>
              Today&apos;s Orders
            </span>

            <strong>
              {currentDayOrders.length}
            </strong>

            <small>
              Current operating day
            </small>
          </div>

          <div className="sd-spark sd-spark-red">
            <i />
            <i />
            <i />
            <i />
          </div>
        </div>


        <div className="sd-metric-card sd-metric-blue">
          <div className="sd-metric-icon">
            <Activity size={22} />
          </div>

          <div className="sd-metric-copy">
            <span>
              Active Orders
            </span>

            <strong>
              {allActiveOrders.length}
            </strong>

            <small>
              Moving through workflow
            </small>
          </div>

          <div className="sd-spark sd-spark-blue">
            <i />
            <i />
            <i />
            <i />
          </div>
        </div>


        <div className="sd-metric-card sd-metric-yellow">
          <div className="sd-metric-icon">
            <CircleCheckBig size={22} />
          </div>

          <div className="sd-metric-copy">
            <span>
              Completed Today
            </span>

            <strong>
              {currentDayPastOrders.filter(
                (order) =>
                  order.status ===
                  "completed"
              ).length}
            </strong>

            <small>
              Successfully closed
            </small>
          </div>

          <div className="sd-spark sd-spark-yellow">
            <i />
            <i />
            <i />
            <i />
          </div>
        </div>


        <div className="sd-metric-card sd-metric-purple">
          <div className="sd-metric-icon">
            <UsersRound size={22} />
          </div>

          <div className="sd-metric-copy">
            <span>
              Customers
            </span>

            <strong>
              {customers.length}
            </strong>

            <small>
              StoreDash businesses
            </small>
          </div>

          <div className="sd-customer-ring">
            <span>
              {customers.length}
            </span>
          </div>
        </div>
      </section>

      <div className="card sd-order-search-card">
        <div className="sd-section-heading">
          <div>
            <span className="sd-section-kicker">
              Quick Search
            </span>

            <h2>
              Find Today&apos;s Order
            </h2>
          </div>
        </div>

        <p className="label">
          Search using the customer's
          order number for this operating
          day.
        </p>


        <input
          className="input"
          style={{
            maxWidth: 350,
            marginTop: 12,
          }}
          value={search}
          onChange={(event) =>
            setSearch(
              event.target.value.replace(
                /\D/g,
                ""
              )
            )
          }
          placeholder="Example: 20"
        />
      </div>


      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <h2>
          Draft Orders
        </h2>

        <p className="label">
          Editable until sourcing,
          pricing and customer agreement
          are complete.
        </p>

        <div
          style={{
            marginTop: 14,
          }}
        >
          {renderOrders(
            visibleDrafts
          )}
        </div>
      </div>


      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <h2>
          Active Orders
        </h2>

        <p className="label">
          Finalized orders currently
          being fulfilled. Any unfinished
          older order remains visible
          here as carryover.
        </p>

        <div
          style={{
            marginTop: 14,
          }}
        >
          {renderOrders(
            visibleActive
          )}
        </div>
      </div>


      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <h2>
          Completed / Closed Today
        </h2>

        <div
          style={{
            marginTop: 14,
          }}
        >
          {renderOrders(
            visiblePast
          )}
        </div>
      </div>
    </>
  );
}
