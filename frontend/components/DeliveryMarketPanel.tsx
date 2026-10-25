"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type DeliverySnapshot = {
  id: number;
  order_id: number;

  status: string;
  provider: string;
  model_version: string;

  goods_total: number;
  service_fee: number;

  route_distance_km:
    number | null;

  route_duration_minutes:
    number | null;

  supplier_stop_count: number;
  item_count: number;

  total_load_units: number;
  total_weight_kg: number;
  total_volume_l: number;

  total_handling_score: number;
  total_fragility_score: number;

  chargeable_weight_kg: number;

  capacity_class: string;
  distance_band: string;

  model_predicted_carrier_cost:
    number;

  model_customer_price:
    number;

  live_market_min:
    number | null;

  live_market_median:
    number | null;

  live_market_recommended:
    number | null;

  selected_carrier_bid_id:
    number | null;

  selected_carrier_cost:
    number | null;

  customer_delivery_fee:
    number | null;

  storedash_delivery_profit:
    number | null;

  storedash_margin_rate:
    number | null;

  pricing_mode:
    string | null;

  customer_decision: string;

  actual_carrier_cost:
    number | null;
};


type CarrierBid = {
  id: number;

  provider: string;

  external_bid_id:
    string | null;

  amount: number;

  pickup_eta_minutes:
    number | null;

  provider_rating:
    number | null;

  vehicle_type:
    string | null;

  vehicle_capacity_kg:
    number | null;

  qualified: boolean;
  capacity_ok: boolean;

  rejection_reason:
    string | null;

  selected: boolean;
};


type MarketSummary = {
  qualified_bid_count: number;

  minimum_bid: number;
  median_bid: number;
  recommended_bid: number;

  bid_spread: number;

  provider: string;
};


type MarketResponse = {
  snapshot: DeliverySnapshot;

  bids: CarrierBid[];

  market_summary:
    MarketSummary | null;
};


type PrepareResponse = {
  message: string;

  snapshot:
    DeliverySnapshot;

  model: {
    engine_version: string;

    capacity_class: string;

    planning_capacity_kg:
      number;

    public_market_anchor:
      number;

    chargeable_weight_kg:
      number;

    distance_band: string;

    predicted_carrier_cost:
      number;

    predicted_customer_price:
      number;

    requires_live_quote:
      boolean;
  };
};


type BidForm = {
  amount: string;

  pickupEta: string;

  rating: string;

  vehicleType: string;

  vehicleCapacity: string;

  externalBidId: string;

  qualified: boolean;

  capacityOk: boolean;

  rejectionReason: string;
};


const emptyBid: BidForm = {
  amount: "",

  pickupEta: "",

  rating: "",

  vehicleType: "",

  vehicleCapacity: "",

  externalBidId: "",

  qualified: true,

  capacityOk: true,

  rejectionReason: "",
};


function money(
  value:
    | number
    | null
    | undefined
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  return `GH₵${Number(
    value
  ).toFixed(2)}`;
}


function pretty(
  value:
    string
    | null
    | undefined
) {
  if (!value) {
    return "—";
  }

  return value
    .replaceAll(
      "_",
      " "
    )
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase()
    );
}


export default function DeliveryMarketPanel({
  orderId,
}: {
  orderId: number;
}) {
  const [
    market,
    setMarket,
  ] = useState<
    MarketResponse | null
  >(null);


  const [
    bid,
    setBid,
  ] = useState<BidForm>(
    emptyBid
  );


  const [
    selectedBidId,
    setSelectedBidId,
  ] = useState<
    number | null
  >(null);


  const [
    busy,
    setBusy,
  ] = useState(false);


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    error,
    setError,
  ] = useState("");


  const [
    message,
    setMessage,
  ] = useState("");


  const loadMarket =
    useCallback(
      async (
        silent = false
      ) => {
        try {
          if (!silent) {
            setLoading(
              true
            );
          }

          const data =
            await api<
              MarketResponse
            >(
              `/orders/${orderId}/delivery-market`
            );

          setMarket(
            data
          );


          const selected =
            data.bids.find(
              (current) =>
                current.selected
            );


          if (selected) {
            setSelectedBidId(
              selected.id
            );
          }

          setError("");

        } catch {
          /*
           * A 404 here simply means
           * the order has not entered
           * the delivery market yet.
           */
          setMarket(
            null
          );

        } finally {
          setLoading(
            false
          );
        }
      },
      [
        orderId,
      ]
    );


  useEffect(() => {
    loadMarket();

  }, [
    loadMarket,
  ]);


  async function prepareMarket() {
    if (
      market &&
      market.bids.length > 0
    ) {
      const proceed =
        window.confirm(
          "Rebuilding the estimate will create a new pricing snapshot. Existing bids stay in history but will not belong to the new quote. Continue?"
        );

      if (!proceed) {
        return;
      }
    }


    try {
      setBusy(true);

      setError("");
      setMessage("");


      const result =
        await api<
          PrepareResponse
        >(
          `/orders/${orderId}/delivery-market/prepare`,
          {
            method:
              "POST",
          }
        );


      setSelectedBidId(
        null
      );


      setMessage(
        `Delivery market prepared using ${result.snapshot.model_version}. Record CargoMov bids before quoting the customer.`
      );


      await loadMarket(
        true
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not prepare delivery market."
      );

    } finally {
      setBusy(false);
    }
  }


  async function addBid() {
    const amount =
      Number(
        bid.amount
      );


    if (
      !Number.isFinite(
        amount
      ) ||
      amount <= 0
    ) {
      setError(
        "Enter a valid CargoMov bid amount."
      );

      return;
    }


    try {
      setBusy(true);

      setError("");
      setMessage("");


      await api(
        `/orders/${orderId}/delivery-market/bids`,
        {
          method:
            "POST",

          body:
            JSON.stringify({
              provider:
                "cargomov",

              external_bid_id:
                bid.externalBidId
                  .trim()
                  || null,

              amount,

              pickup_eta_minutes:
                bid.pickupEta
                  ? Number(
                      bid.pickupEta
                    )
                  : null,

              provider_rating:
                bid.rating
                  ? Number(
                      bid.rating
                    )
                  : null,

              vehicle_type:
                bid.vehicleType
                  .trim()
                  || null,

              vehicle_capacity_kg:
                bid.vehicleCapacity
                  ? Number(
                      bid.vehicleCapacity
                    )
                  : null,

              qualified:
                bid.qualified,

              capacity_ok:
                bid.capacityOk,

              rejection_reason:
                bid.rejectionReason
                  .trim()
                  || null,
            }),
        }
      );


      setBid(
        emptyBid
      );


      setMessage(
        "CargoMov bid recorded permanently."
      );


      await loadMarket(
        true
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not record CargoMov bid."
      );

    } finally {
      setBusy(false);
    }
  }


  async function finalizePrice() {
    if (!selectedBidId) {
      setError(
        "Select a qualified CargoMov bid first."
      );

      return;
    }


    try {
      setBusy(true);

      setError("");
      setMessage("");


      await api(
        `/orders/${orderId}/delivery-market/finalize`,
        {
          method:
            "POST",

          body:
            JSON.stringify({
              bid_id:
                selectedBidId,
            }),
        }
      );


      await loadMarket(
        true
      );


      setMessage(
        "Final customer delivery price generated. Give the customer this one final price."
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not generate final customer price."
      );

    } finally {
      setBusy(false);
    }
  }


  async function customerDecision(
    decision:
      | "accepted"
      | "declined"
  ) {
    if (
      decision ===
        "declined"
      &&
      !window.confirm(
        "The customer declined the final price. This quote will stay permanently in StoreDash history and the order will be cancelled. Continue?"
      )
    ) {
      return;
    }


    try {
      setBusy(true);

      setError("");
      setMessage("");


      await api(
        `/orders/${orderId}/delivery-market/customer-decision`,
        {
          method:
            "POST",

          body:
            JSON.stringify({
              decision,
            }),
        }
      );


      await loadMarket(
        true
      );


      if (
        decision ===
        "accepted"
      ) {
        setMessage(
          "Customer accepted. You may now confirm the intended CargoMov bid and continue dispatch."
        );
      } else {
        setMessage(
          "Customer declined. The quote and market data were preserved for learning."
        );
      }


      window.setTimeout(
        () => {
          window.location.reload();
        },
        700
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not record customer decision."
      );

    } finally {
      setBusy(false);
    }
  }


  if (loading) {
    return (
      <div
        className="card"
        style={{
          marginTop:
            20,
        }}
      >
        Loading delivery market...
      </div>
    );
  }


  const snapshot =
    market?.snapshot ??
    null;


  const bids =
    market?.bids ??
    [];


  const summary =
    market?.market_summary ??
    null;


  const selectedBid =
    bids.find(
      (current) =>
        current.id ===
        selectedBidId
    ) ??
    bids.find(
      (current) =>
        current.selected
    ) ??
    null;


  const canAddBids =
    snapshot?.status ===
      "awaiting_carrier_bids";


  const canFinalize =
    snapshot?.status ===
      "awaiting_carrier_bids";


  const awaitingCustomer =
    snapshot?.status ===
      "customer_quote_ready";


  return (
    <div
      className="card"
      style={{
        marginTop:
          20,
      }}
    >
      <div className="header">
        <div>
          <h2>
            Delivery Market
          </h2>

          <p className="label">
            StoreDash estimates the market,
            CargoMov provides live supply,
            and the customer receives one
            final delivery price.
          </p>
        </div>

        <button
          className="btn btn-secondary"
          disabled={
            busy
          }
          onClick={
            prepareMarket
          }
        >
          {
            snapshot
              ? "Rebuild Estimate"
              : "Prepare Delivery Market"
          }
        </button>
      </div>


      {error && (
        <div
          className="notice"
          style={{
            marginTop:
              14,
          }}
        >
          {error}
        </div>
      )}


      {message && (
        <div
          className="notice"
          style={{
            marginTop:
              14,
          }}
        >
          {message}
        </div>
      )}


      {!snapshot && (
        <div
          style={{
            marginTop:
              18,
          }}
        >
          <strong>
            No delivery-market snapshot yet.
          </strong>

          <p className="label">
            Finish supplier sourcing and
            logistics classification, then
            prepare the delivery market.
          </p>
        </div>
      )}


      {snapshot && (
        <>
          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "repeat(auto-fit, minmax(180px, 1fr))",

              gap:
                12,

              marginTop:
                18,
            }}
          >
            <Metric
              label="Model Version"
              value={
                snapshot.model_version
              }
            />

            <Metric
              label="Capacity Class"
              value={
                pretty(
                  snapshot.capacity_class
                )
              }
            />

            <Metric
              label="Route"
              value={
                snapshot.route_distance_km
                  !== null
                  ? `${snapshot.route_distance_km.toFixed(1)} km`
                  : "—"
              }
            />

            <Metric
              label="Route Time"
              value={
                snapshot.route_duration_minutes
                  !== null
                  ? `${snapshot.route_duration_minutes.toFixed(0)} min`
                  : "—"
              }
            />

            <Metric
              label="Chargeable Load"
              value={
                `${snapshot.chargeable_weight_kg.toFixed(1)} kg`
              }
            />

            <Metric
              label="Supplier Stops"
              value={
                String(
                  snapshot.supplier_stop_count
                )
              }
            />
          </div>


          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "repeat(auto-fit, minmax(210px, 1fr))",

              gap:
                12,

              marginTop:
                14,
            }}
          >
            <Metric
              label="Predicted Carrier Market"
              value={
                money(
                  snapshot.model_predicted_carrier_cost
                )
              }
            />

            <Metric
              label="StoreDash Fair Customer Model"
              value={
                money(
                  snapshot.model_customer_price
                )
              }
            />

            <Metric
              label="Live Market Median"
              value={
                money(
                  snapshot.live_market_median
                  ??
                  summary?.median_bid
                )
              }
            />

            <Metric
              label="Live Market Recommended"
              value={
                money(
                  snapshot.live_market_recommended
                  ??
                  summary?.recommended_bid
                )
              }
            />
          </div>


          {canAddBids && (
            <div
              style={{
                borderTop:
                  "1px solid #e5e7eb",

                marginTop:
                  22,

                paddingTop:
                  20,
              }}
            >
              <h3>
                Record CargoMov Bid
              </h3>

              <p className="label">
                Record every serious bid,
                including rejected or
                capacity-mismatch bids.
              </p>


              <div
                className="form-grid"
                style={{
                  marginTop:
                    12,
                }}
              >
                <input
                  className="input"
                  type="number"
                  min="0.01"
                  step="0.50"
                  placeholder="Bid amount GH₵"
                  value={
                    bid.amount
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      amount:
                        event
                          .target
                          .value,
                    })
                  }
                />

                <input
                  className="input"
                  placeholder="Vehicle type"
                  value={
                    bid.vehicleType
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      vehicleType:
                        event
                          .target
                          .value,
                    })
                  }
                />

                <input
                  className="input"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Pickup ETA minutes"
                  value={
                    bid.pickupEta
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      pickupEta:
                        event
                          .target
                          .value,
                    })
                  }
                />

                <input
                  className="input"
                  type="number"
                  min="0"
                  max="5"
                  step="0.1"
                  placeholder="Driver rating"
                  value={
                    bid.rating
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      rating:
                        event
                          .target
                          .value,
                    })
                  }
                />

                <input
                  className="input"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Vehicle capacity kg"
                  value={
                    bid.vehicleCapacity
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      vehicleCapacity:
                        event
                          .target
                          .value,
                    })
                  }
                />

                <input
                  className="input"
                  placeholder="CargoMov bid ID (optional)"
                  value={
                    bid.externalBidId
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      externalBidId:
                        event
                          .target
                          .value,
                    })
                  }
                />
              </div>


              <div
                style={{
                  display:
                    "flex",

                  gap:
                    18,

                  flexWrap:
                    "wrap",

                  marginTop:
                    14,
                }}
              >
                <label>
                  <input
                    type="checkbox"
                    checked={
                      bid.capacityOk
                    }
                    onChange={(
                      event
                    ) =>
                      setBid({
                        ...bid,

                        capacityOk:
                          event
                            .target
                            .checked,
                      })
                    }
                  />

                  {" "}
                  Capacity fits
                </label>


                <label>
                  <input
                    type="checkbox"
                    checked={
                      bid.qualified
                    }
                    onChange={(
                      event
                    ) =>
                      setBid({
                        ...bid,

                        qualified:
                          event
                            .target
                            .checked,
                      })
                    }
                  />

                  {" "}
                  Qualified bid
                </label>
              </div>


              {(
                !bid.capacityOk ||
                !bid.qualified
              ) && (
                <textarea
                  className="textarea"
                  style={{
                    marginTop:
                      12,
                  }}
                  placeholder="Why was this bid rejected?"
                  value={
                    bid.rejectionReason
                  }
                  onChange={(
                    event
                  ) =>
                    setBid({
                      ...bid,

                      rejectionReason:
                        event
                          .target
                          .value,
                    })
                  }
                />
              )}


              <button
                className="btn"
                disabled={
                  busy
                }
                style={{
                  marginTop:
                    14,
                }}
                onClick={
                  addBid
                }
              >
                Record CargoMov Bid
              </button>
            </div>
          )}


          <div
            style={{
              borderTop:
                "1px solid #e5e7eb",

              marginTop:
                22,

              paddingTop:
                20,
            }}
          >
            <div className="header">
              <div>
                <h3>
                  CargoMov Bids
                </h3>

                <p className="label">
                  Choose the intended
                  qualified bid. Do not
                  accept the carrier yet.
                </p>
              </div>

              {summary && (
                <div className="label">
                  {
                    summary
                      .qualified_bid_count
                  } qualified
                </div>
              )}
            </div>


            {bids.length === 0 ? (
              <div
                className="notice"
                style={{
                  marginTop:
                    12,
                }}
              >
                No CargoMov bids recorded yet.
              </div>
            ) : (
              <div
                style={{
                  display:
                    "grid",

                  gap:
                    10,

                  marginTop:
                    12,
                }}
              >
                {bids.map(
                  (
                    current
                  ) => {
                    const usable =
                      current.qualified
                      &&
                      current.capacity_ok;


                    return (
                      <label
                        key={
                          current.id
                        }
                        style={{
                          display:
                            "grid",

                          gridTemplateColumns:
                            "auto 1fr auto",

                          gap:
                            12,

                          alignItems:
                            "center",

                          padding:
                            14,

                          border:
                            current.selected
                              ? "2px solid #111827"
                              : "1px solid #e5e7eb",

                          borderRadius:
                            12,

                          opacity:
                            usable
                              ? 1
                              : 0.65,
                        }}
                      >
                        <input
                          type="radio"
                          name="carrier-bid"
                          disabled={
                            !usable ||
                            !canFinalize
                          }
                          checked={
                            selectedBidId ===
                            current.id
                          }
                          onChange={() =>
                            setSelectedBidId(
                              current.id
                            )
                          }
                        />


                        <div>
                          <strong>
                            {
                              money(
                                current.amount
                              )
                            }
                          </strong>

                          <div className="label">
                            {
                              current.vehicle_type
                              ||
                              "Vehicle not recorded"
                            }

                            {
                              current.pickup_eta_minutes
                              !== null
                                ? ` · ETA ${current.pickup_eta_minutes} min`
                                : ""
                            }

                            {
                              current.provider_rating
                              !== null
                                ? ` · Rating ${current.provider_rating.toFixed(1)}`
                                : ""
                            }
                          </div>

                          {!usable && (
                            <div
                              className="label"
                              style={{
                                marginTop:
                                  4,
                              }}
                            >
                              {
                                !current.capacity_ok
                                  ? "CAPACITY MISMATCH"
                                  : "NOT QUALIFIED"
                              }

                              {
                                current.rejection_reason
                                  ? ` · ${current.rejection_reason}`
                                  : ""
                              }
                            </div>
                          )}
                        </div>


                        <div className="label">
                          {
                            current.selected
                              ? "SELECTED"
                              : usable
                                ? "QUALIFIED"
                                : "REJECTED"
                          }
                        </div>
                      </label>
                    );
                  }
                )}
              </div>
            )}


            {canFinalize && (
              <button
                className="btn"
                disabled={
                  busy ||
                  !selectedBidId
                }
                style={{
                  marginTop:
                    16,
                }}
                onClick={
                  finalizePrice
                }
              >
                Generate Final Customer Price
              </button>
            )}
          </div>


          {snapshot.customer_delivery_fee !==
            null && (
            <div
              style={{
                borderTop:
                  "1px solid #e5e7eb",

                marginTop:
                  22,

                paddingTop:
                  20,
              }}
            >
              <h3>
                Final Delivery Economics
              </h3>


              <div
                style={{
                  display:
                    "grid",

                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(190px, 1fr))",

                  gap:
                    12,

                  marginTop:
                    12,
                }}
              >
                <Metric
                  label="StoreDash Model Price"
                  value={
                    money(
                      snapshot.model_customer_price
                    )
                  }
                />

                <Metric
                  label="Selected CargoMov Cost"
                  value={
                    money(
                      snapshot.selected_carrier_cost
                    )
                  }
                />

                <Metric
                  label="Customer Delivery Fee"
                  value={
                    money(
                      snapshot.customer_delivery_fee
                    )
                  }
                />

                <Metric
                  label="StoreDash Delivery Profit"
                  value={
                    money(
                      snapshot.storedash_delivery_profit
                    )
                  }
                />

                <Metric
                  label="Delivery Margin"
                  value={
                    snapshot.storedash_margin_rate
                    !== null
                      ? `${(
                          snapshot.storedash_margin_rate
                          * 100
                        ).toFixed(1)}%`
                      : "—"
                  }
                />

                <Metric
                  label="Pricing Policy"
                  value={
                    pretty(
                      snapshot.pricing_mode
                    )
                  }
                />
              </div>


              <div
                className="notice"
                style={{
                  marginTop:
                    14,
                }}
              >
                Customer receives the final
                delivery fee only. Internal
                carrier bids and StoreDash
                margin are not part of the
                customer negotiation.
              </div>
            </div>
          )}


          {awaitingCustomer && (
            <div
              style={{
                borderTop:
                  "1px solid #e5e7eb",

                marginTop:
                  22,

                paddingTop:
                  20,
              }}
            >
              <h3>
                Customer Decision
              </h3>

              <p className="label">
                Give the customer one final
                quote. There is no bargaining
                or wait-price state.
              </p>


              <div
                style={{
                  display:
                    "flex",

                  gap:
                    12,

                  flexWrap:
                    "wrap",

                  marginTop:
                    14,
                }}
              >
                <button
                  className="btn"
                  disabled={
                    busy
                  }
                  onClick={() =>
                    customerDecision(
                      "accepted"
                    )
                  }
                >
                  Customer Accepted
                </button>


                <button
                  className="btn btn-secondary"
                  disabled={
                    busy
                  }
                  onClick={() =>
                    customerDecision(
                      "declined"
                    )
                  }
                >
                  Customer Declined
                </button>
              </div>
            </div>
          )}


          {snapshot.status ===
            "customer_accepted" && (
            <div
              className="notice"
              style={{
                marginTop:
                  20,
              }}
            >
              Customer accepted. Now confirm
              the selected CargoMov bid
              {
                selectedBid
                  ? ` (${money(
                      selectedBid.amount
                    )})`
                  : ""
              }
              {" "}
              and proceed to dispatch.
            </div>
          )}


          {snapshot.status ===
            "customer_declined" && (
            <div
              className="notice"
              style={{
                marginTop:
                  20,
              }}
            >
              Customer declined. This order,
              quote, bids and pricing result
              remain stored for StoreDash
              market learning.
            </div>
          )}
        </>
      )}
    </div>
  );
}


function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      style={{
        border:
          "1px solid #e5e7eb",

        borderRadius:
          12,

        padding:
          14,
      }}
    >
      <div className="label">
        {label}
      </div>

      <strong
        style={{
          display:
            "block",

          marginTop:
            5,
        }}
      >
        {value}
      </strong>
    </div>
  );
}
