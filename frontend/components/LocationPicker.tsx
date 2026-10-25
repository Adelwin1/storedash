"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type LocationResult = {
  display_name: string;
  latitude: number;
  longitude: number;
  type: string | null;
};

export default function LocationPicker({
  entityType,
  entityId,
  initialLocation,
  onSaved,
}: {
  entityType: "supplier" | "business";
  entityId: number;
  initialLocation?: string | null;
  onSaved?: (location: string) => void;
}) {
  const [query, setQuery] = useState(
    initialLocation || ""
  );

  const [results, setResults] = useState<
    LocationResult[]
  >([]);

  const [searching, setSearching] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [error, setError] =
    useState("");

  async function search() {
    if (query.trim().length < 3) {
      setError(
        "Enter at least 3 characters."
      );
      return;
    }

    try {
      setSearching(true);
      setError("");
      setMessage("");

      const data = await api<
        LocationResult[]
      >(
        `/locations/search?q=${encodeURIComponent(
          query.trim()
        )}`
      );

      setResults(data);

      if (data.length === 0) {
        setMessage(
          "No matching locations found."
        );
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not search locations."
      );
    } finally {
      setSearching(false);
    }
  }

  async function save(
    result: LocationResult
  ) {
    try {
      setSaving(true);
      setError("");
      setMessage("");

      const url =
        entityType === "supplier"
          ? `/suppliers/${entityId}/location`
          : `/businesses/${entityId}/location`;

      const body =
        entityType === "supplier"
          ? {
              location:
                result.display_name,

              latitude:
                result.latitude,

              longitude:
                result.longitude,
            }
          : {
              address:
                result.display_name,

              latitude:
                result.latitude,

              longitude:
                result.longitude,
            };

      await api(url, {
        method: "PATCH",
        body: JSON.stringify(body),
      });

      setQuery(
        result.display_name
      );

      setResults([]);

      setMessage(
        "Location saved."
      );

      onSaved?.(
        result.display_name
      );
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not save location."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        marginTop: 18,
      }}
    >
      <h3>Delivery Location</h3>

      <p className="label">
        Search for the actual pickup or
        delivery point. StoreDash will
        save the selected coordinates.
      </p>

      <div
        style={{
          display: "flex",
          gap: 10,
          marginTop: 12,
        }}
      >
        <input
          className="input"
          value={query}
          placeholder="Adum, Kumasi"
          onChange={(event) =>
            setQuery(
              event.target.value
            )
          }
          onKeyDown={(event) => {
            if (
              event.key === "Enter"
            ) {
              event.preventDefault();
              search();
            }
          }}
        />

        <button
          type="button"
          className="btn btn-secondary"
          onClick={search}
          disabled={searching}
        >
          {searching
            ? "Searching..."
            : "Search Location"}
        </button>
      </div>

      {results.length > 0 && (
        <div
          style={{
            marginTop: 14,
            display: "grid",
            gap: 8,
          }}
        >
          {results.map(
            (
              result,
              index
            ) => (
              <button
                key={`${result.latitude}-${result.longitude}-${index}`}
                type="button"
                disabled={saving}
                onClick={() =>
                  save(result)
                }
                style={{
                  textAlign: "left",
                  width: "100%",
                  padding: 12,
                  border:
                    "1px solid #e5e7eb",
                  borderRadius: 8,
                  background:
                    "white",
                  cursor:
                    saving
                      ? "wait"
                      : "pointer",
                }}
              >
                <strong>
                  {
                    result.display_name
                  }
                </strong>

                <div
                  className="label"
                  style={{
                    marginTop: 4,
                  }}
                >
                  {result.type ||
                    "location"}
                </div>
              </button>
            )
          )}
        </div>
      )}

      {message && (
        <div
          className="notice"
          style={{
            marginTop: 12,
          }}
        >
          {message}
        </div>
      )}

      {error && (
        <div
          className="error"
          style={{
            marginTop: 12,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
