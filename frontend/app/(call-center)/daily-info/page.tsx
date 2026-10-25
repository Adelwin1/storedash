"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type OperatingDay = {
  id: number;
  business_date: string;
  opened_at: string;
  closed_at: string | null;
  is_closed: boolean;
  closed_by_id: number | null;
  notes: string | null;
};


export default function DailyInfoPage() {
  const [days, setDays] =
    useState<OperatingDay[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {
    async function loadDays() {
      try {
        const data =
          await api<
            OperatingDay[]
          >(
            "/operating-days"
          );

        setDays(
          data
        );

      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Could not load daily information."
        );

      } finally {
        setLoading(
          false
        );
      }
    }

    loadDays();
  }, []);


  if (loading) {
    return (
      <div className="card">
        Loading daily information...
      </div>
    );
  }


  return (
    <>
      <div className="header">
        <div>
          <h1>
            Daily Info
          </h1>

          <p className="label">
            StoreDash operating-day
            archive.
          </p>
        </div>


        <Link
          href="/dashboard"
          className="btn btn-secondary"
        >
          Dashboard
        </Link>
      </div>


      {error && (
        <div className="notice">
          {error}
        </div>
      )}


      <div className="card">
        {days.length === 0 ? (
          <div className="empty-state">
            No operating days yet.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>
                  Date
                </th>

                <th>
                  Status
                </th>

                <th>
                  Opened
                </th>

                <th>
                  Closed
                </th>

                <th></th>
              </tr>
            </thead>

            <tbody>
              {days.map(
                (day) => (
                  <tr
                    key={
                      day.id
                    }
                  >
                    <td>
                      <strong>
                        {
                          day.business_date
                        }
                      </strong>
                    </td>

                    <td>
                      <span className="badge">
                        {day.is_closed
                          ? "CLOSED"
                          : "OPEN"}
                      </span>
                    </td>

                    <td>
                      {new Date(
                        day.opened_at
                      ).toLocaleString()}
                    </td>

                    <td>
                      {day.closed_at
                        ? new Date(
                            day.closed_at
                          ).toLocaleString()
                        : "—"}
                    </td>

                    <td>
                      <Link
                        className="btn btn-secondary"
                        href={
                          `/daily-info/${day.id}`
                        }
                      >
                        Open
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
