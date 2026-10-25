"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import { api } from "@/lib/api";


type Driver = {
  id: number;
  name: string;
  phone: string;
  vehicle_type: string;
  is_available: boolean;
  is_active: boolean;
};


type RoutingStatus = {
  driver_id: number;
  driver_name: string;

  is_active: boolean;
  is_available: boolean;

  routing_profile_complete: boolean;

  driver_vehicle_id:
    number | null;

  vehicle_spec_id:
    number | null;

  registration:
    string | null;

  reason:
    string | null;
};


type DispatchPool = {
  count: number;
  order_ids: number[];
  status: string;
};


type BatchStop = {
  sequence: number;

  key: string;

  stop_type: string;

  supplier_id:
    number | null;

  order_id:
    number | null;

  related_order_ids:
    number[];

  location_label:
    string | null;

  travel_from_previous_km:
    number;

  travel_from_previous_minutes:
    number;

  arrival_minutes:
    number;

  service_minutes:
    number;

  weight_delta_kg:
    number;

  volume_delta_l:
    number;

  load_weight_after_kg:
    number;

  load_volume_after_l:
    number;

  weight_utilization:
    number;

  volume_utilization:
    number;
};


type BatchPlan = {
  planner_version: string;

  feasible: boolean;

  rejection_reason:
    string | null;

  order_ids: number[];

  order_count: number;

  pickup_count: number;

  delivery_count: number;

  total_distance_km: number;

  total_driving_minutes: number;

  total_service_minutes: number;

  total_route_minutes: number;

  peak_weight_kg: number;

  peak_volume_l: number;

  peak_weight_utilization: number;

  peak_volume_utilization: number;

  customer_delivery_revenue: number;

  road_provider:
    string | null;

  traffic_aware: boolean;

  stops: BatchStop[];
};


type ManualPreview = {
  version: string;

  driver_id: number;

  driver_name: string;

  driver_vehicle_id: number;

  vehicle: {
    manufacturer: string;
    model: string;

    variant:
      string | null;

    registration:
      string | null;
  };

  capacity: {
    max_payload_kg: number;

    max_volume_l: number;

    safe_capacity_ratio: number;

    physical_payload_kg:
      number;

    physical_volume_l:
      number;

    seat_volume_enabled:
      boolean;
  };

  selected_order_ids:
    number[];

  plan: BatchPlan;

  pricing: {
    predicted_driver_payout:
      number;

    predicted_contribution:
      number;

    predicted_margin_rate:
      number;

    policy_version:
      string;

    economics_version:
      string;
  } | null;

  message: string;
};


type AutoRecommendation = {
  chosen_order_ids:
    number[];

  plan:
    BatchPlan | null;

  blocked?: {
    order_id: number;
    reason: string;
  }[];

  message?: string;
};


type MaterializedBatch = {
  batch_id: number;

  status: string;

  driver_id: number;

  driver_vehicle_id:
    number;

  order_count: number;

  predicted_driver_payout:
    number | null;
};


type DriverOfferResponse = {
  id?: number;
  offer_id?: number;
};


function humanizeReason(
  value:
    string | null
) {

  if (!value) {
    return (
      "This route is not feasible."
    );
  }

  return value
    .replaceAll(
      "_",
      " "
    )
    .replace(
      /^order (\d+) exceeds vehicle weight$/i,
      "Order $1 exceeds this vehicle's safe weight capacity."
    )
    .replace(
      /^order (\d+) exceeds vehicle volume$/i,
      "Order $1 exceeds this vehicle's safe volume capacity."
    );
}


function sameOrderIds(
  left: number[],
  right: number[],
) {

  if (
    left.length
    !==
    right.length
  ) {
    return false;
  }

  const a = [
    ...left,
  ].sort(
    (x, y) =>
      x - y
  );

  const b = [
    ...right,
  ].sort(
    (x, y) =>
      x - y
  );

  return a.every(
    (value, index) =>
      value
      ===
      b[index]
  );
}


export default function DispatchPage() {

  const [
    drivers,
    setDrivers,
  ] = useState<
    Driver[]
  >([]);


  const [
    routingStatuses,
    setRoutingStatuses,
  ] = useState<
    RoutingStatus[]
  >([]);


  const [
    pool,
    setPool,
  ] = useState<
    DispatchPool | null
  >(null);


  const [
    selectedDriverId,
    setSelectedDriverId,
  ] = useState("");


  const [
    selectedOrderIds,
    setSelectedOrderIds,
  ] = useState<
    number[]
  >([]);


  const [
    requestedOrderId,
    setRequestedOrderId,
  ] = useState<
    number | null
  >(null);


  const [
    preview,
    setPreview,
  ] = useState<
    ManualPreview | null
  >(null);


  const [
    previewing,
    setPreviewing,
  ] = useState(false);


  const [
    busy,
    setBusy,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  const [
    message,
    setMessage,
  ] = useState("");


  const initialOrderApplied =
    useRef(false);


  const previewVersion =
    useRef(0);


  function routingStatusFor(
    driverId: number
  ) {

    return routingStatuses.find(
      (status) =>
        status.driver_id
        ===
        driverId
    );
  }


  function driverReady(
    driver: Driver,
    statuses:
      RoutingStatus[]
        =
      routingStatuses
  ) {

    const routing =
      statuses.find(
        (status) =>
          status.driver_id
          ===
          driver.id
      );


    return (
      driver.is_active
      &&
      driver.is_available
      &&
      routing
        ?.routing_profile_complete
        === true
    );
  }


  async function refresh() {

    try {

      const [
        driverData,
        poolData,
        routingData,
      ] = await Promise.all([
        api<Driver[]>(
          "/drivers?active_only=false"
        ),

        api<DispatchPool>(
          "/batching/pool"
        ),

        api<RoutingStatus[]>(
          "/drivers/routing-status"
        ),
      ]);


      setDrivers(
        driverData
      );


      setRoutingStatuses(
        routingData
      );


      setPool(
        poolData
      );


      setSelectedOrderIds(
        (current) =>
          current.filter(
            (orderId) =>
              poolData.order_ids.includes(
                orderId
              )
          )
      );


      setSelectedDriverId(
        (current) => {

          const existing =
            driverData.find(
              (driver) =>
                String(
                  driver.id
                )
                ===
                current
            );


          if (
            existing
            &&
            driverReady(
              existing,
              routingData
            )
          ) {
            return current;
          }


          const firstReady =
            driverData.find(
              (driver) =>
                driverReady(
                  driver,
                  routingData
                )
            );


          return firstReady
            ? String(
                firstReady.id
              )
            : "";
        }
      );


      if (
        !initialOrderApplied
          .current
      ) {

        initialOrderApplied.current =
          true;


        if (
          typeof window
          !==
          "undefined"
        ) {

          const params =
            new URLSearchParams(
              window.location.search
            );


          const raw =
            params.get(
              "orderId"
            );


          if (raw) {

            const orderId =
              Number(
                raw
              );


            if (
              Number.isInteger(
                orderId
              )
              &&
              orderId > 0
            ) {

              setRequestedOrderId(
                orderId
              );


              if (
                poolData
                  .order_ids
                  .includes(
                    orderId
                  )
              ) {

                setSelectedOrderIds(
                  [
                    orderId,
                  ]
                );


                setMessage(
                  `Order ${orderId} is ready to build into a driver route.`
                );

              } else {

                setError(
                  `Order ${orderId} is not currently in the dispatch pool.`
                );
              }
            }
          }
        }
      }


    } catch (caught) {

      setError(
        caught instanceof Error
          ? caught.message
          : "Could not load dispatch."
      );
    }
  }


  useEffect(
    () => {
      void refresh();
    },
    []
  );


  useEffect(
    () => {

      if (
        !selectedDriverId
        ||
        selectedOrderIds
          .length === 0
      ) {

        previewVersion.current +=
          1;

        setPreview(
          null
        );

        setPreviewing(
          false
        );

        return;
      }


      const version =
        previewVersion.current
        + 1;


      previewVersion.current =
        version;


      const timer =
        window.setTimeout(
          () => {

            void (
              async () => {

                try {

                  setPreviewing(
                    true
                  );


                  const data =
                    await api<
                      ManualPreview
                    >(
                      "/batching/preview",
                      {
                        method:
                          "POST",

                        body:
                          JSON.stringify({
                            driver_id:
                              Number(
                                selectedDriverId
                              ),

                            order_ids:
                              selectedOrderIds,

                            duration_multiplier:
                              1.0,
                          }),
                      }
                    );


                  if (
                    previewVersion
                      .current
                    !==
                    version
                  ) {
                    return;
                  }


                  setPreview(
                    data
                  );


                  setError(
                    ""
                  );


                } catch (
                  caught
                ) {

                  if (
                    previewVersion
                      .current
                    !==
                    version
                  ) {
                    return;
                  }


                  setPreview(
                    null
                  );


                  setError(
                    caught
                    instanceof Error
                      ? caught.message
                      : "Could not preview this route."
                  );


                } finally {

                  if (
                    previewVersion
                      .current
                    ===
                    version
                  ) {

                    setPreviewing(
                      false
                    );
                  }
                }
              }
            )();
          },
          300
        );


      return () => {
        window.clearTimeout(
          timer
        );
      };

    },
    [
      selectedDriverId,
      selectedOrderIds,
    ]
  );


  function toggleOrder(
    orderId: number
  ) {

    if (busy) {
      return;
    }


    setError(
      ""
    );


    setMessage(
      ""
    );


    setSelectedOrderIds(
      (current) => {

        if (
          current.includes(
            orderId
          )
        ) {

          return current.filter(
            (value) =>
              value
              !==
              orderId
          );
        }


        if (
          current.length
          >=
          12
        ) {

          setError(
            "A route can contain at most 12 orders."
          );

          return current;
        }


        return [
          ...current,
          orderId,
        ];
      }
    );
  }


  async function autoPickOrders() {

    if (
      !selectedDriverId
    ) {

      setError(
        "Choose a rider first."
      );

      return;
    }


    try {

      setBusy(
        true
      );

      setError(
        ""
      );

      setMessage(
        ""
      );


      const data =
        await api<
          AutoRecommendation
        >(
          "/batching/recommend",
          {
            method:
              "POST",

            body:
              JSON.stringify({
                driver_id:
                  Number(
                    selectedDriverId
                  ),

                max_orders:
                  8,

                candidate_limit:
                  20,

                duration_multiplier:
                  1.0,
              }),
          }
        );


      if (
        !data.plan
        ||
        !data.chosen_order_ids
          .length
      ) {

        const blocked =
          (
            data.blocked
            || []
          )
            .slice(
              0,
              4
            )
            .map(
              (item) =>
                `Order ${item.order_id}: ${humanizeReason(
                  item.reason
                )}`
            )
            .join(
              " "
            );


        setError(
          data.message
          ||
          blocked
          ||
          "No feasible automatic batch was found."
        );

        return;
      }


      setSelectedOrderIds(
        data.chosen_order_ids
      );


      setMessage(
        `StoreDash selected ${data.chosen_order_ids.length} orders. You can still add or remove orders before driver approval.`
      );


    } catch (
      caught
    ) {

      setError(
        caught instanceof Error
          ? caught.message
          : "Could not recommend orders."
      );


    } finally {

      setBusy(
        false
      );
    }
  }


  const [
    pendingDriverBatch,
    setPendingDriverBatch,
  ] = useState<
    MaterializedBatch | null
  >(null);


  const [
    pendingDriverOfferId,
    setPendingDriverOfferId,
  ] = useState<
    number | null
  >(null);


  const [
    pendingDriverOrderIds,
    setPendingDriverOrderIds,
  ] = useState<number[]>(
    []
  );


  async function markDriverDeclined() {

    if (
      !pendingDriverBatch
      ||
      pendingDriverOfferId
        == null
    ) {

      setError(
        "Send the route to the driver first."
      );

      return;
    }


    try {

      setBusy(
        true
      );

      setError(
        ""
      );

      setMessage(
        ""
      );


      const declinedBatchId =
        pendingDriverBatch.batch_id;


      await api(
        `/batching/${declinedBatchId}/driver-offers/${pendingDriverOfferId}/decline`,
        {
          method:
            "POST",
        }
      );


      setPendingDriverBatch(
        null
      );

      setPendingDriverOfferId(
        null
      );

      setPendingDriverOrderIds(
        []
      );

      setSelectedDriverId(
        ""
      );

      setPreview(
        null
      );


      setMessage(
        `Driver declined Batch ${declinedBatchId}. Orders were released back to Dispatch. Choose another rider.`
      );


      await refresh();


    } catch (
      caught
    ) {

      setError(
        caught instanceof Error
          ? caught.message
          : "Could not record driver decline."
      );


    } finally {

      setBusy(
        false
      );
    }
  }


  async function sendToDriver() {

    if (
      !preview
      ||
      !preview.plan.feasible
      ||
      !preview.pricing
    ) {

      setError(
        "The selected route must be feasible before sending it to the driver."
      );

      return;
    }


    if (
      !sameOrderIds(
        preview.selected_order_ids,
        selectedOrderIds
      )
    ) {

      setError(
        "The order selection changed. Wait for the latest route preview."
      );

      return;
    }


    if (
      preview.driver_id
      !==
      Number(
        selectedDriverId
      )
    ) {

      setError(
        "The selected rider changed. Wait for the latest route preview."
      );

      return;
    }


    let createdBatchId:
      number | null = null;


    try {

      setBusy(
        true
      );

      setError(
        ""
      );

      setMessage(
        ""
      );


      const batch =
        await api<
          MaterializedBatch
        >(
          "/batching/materialize",
          {
            method:
              "POST",

            body:
              JSON.stringify({
                driver_id:
                  Number(
                    selectedDriverId
                  ),

                order_ids:
                  selectedOrderIds,

                duration_multiplier:
                  1.0,
              }),
          }
        );


      createdBatchId =
        batch.batch_id;


      const offer =
        await api<
          DriverOfferResponse
        >(
          `/batching/${batch.batch_id}/driver-offers`,
          {
            method:
              "POST",

            body:
              JSON.stringify(
                {}
              ),
          }
        );


      const offerId =
        Number(
          offer.offer_id
          ??
          offer.id
        );


      if (
        !Number.isFinite(
          offerId
        )
      ) {

        throw new Error(
          "Driver offer was created without a valid offer ID."
        );
      }


      setPendingDriverBatch(
        batch
      );

      setPendingDriverOfferId(
        offerId
      );

      setPendingDriverOrderIds(
        [
          ...selectedOrderIds,
        ]
      );


      setMessage(
        `Batch ${batch.batch_id} sent to driver. AWAITING DRIVER RESPONSE.`
      );


    } catch (
      caught
    ) {

      const base =
        caught instanceof Error
          ? caught.message
          : "Could not send route to driver.";


      if (
        createdBatchId
        != null
      ) {

        setError(
          `${base} Batch ${createdBatchId} already exists. Do not create a duplicate route.`
        );

      } else {

        setError(
          base
        );
      }


    } finally {

      setBusy(
        false
      );
    }
  }


  async function acceptPendingDriver() {

    if (
      !pendingDriverBatch
      ||
      pendingDriverOfferId
        == null
    ) {

      setError(
        "There is no pending driver response."
      );

      return;
    }


    try {

      setBusy(
        true
      );

      setError(
        ""
      );

      setMessage(
        ""
      );


      const batchId =
        pendingDriverBatch.batch_id;


      await api(
        `/batching/${batchId}/driver-offers/${pendingDriverOfferId}/accept`,
        {
          method:
            "POST",

          body:
            JSON.stringify(
              {}
            ),
        }
      );


      const assignedOrders = [
        ...pendingDriverOrderIds,
      ];


      setPendingDriverBatch(
        null
      );

      setPendingDriverOfferId(
        null
      );

      setPendingDriverOrderIds(
        []
      );

      setSelectedOrderIds(
        []
      );

      setPreview(
        null
      );

      setRequestedOrderId(
        null
      );


      setMessage(
        `Batch ${batchId} accepted. Driver assigned and dispatched for orders ${assignedOrders.join(
          ", "
        )}.`
      );


      await refresh();


    } catch (
      caught
    ) {

      setError(
        caught instanceof Error
          ? caught.message
          : "Could not dispatch accepted driver."
      );


    } finally {

      setBusy(
        false
      );
    }
  }


  const selectedDriver =
    drivers.find(
      (driver) =>
        String(
          driver.id
        )
        ===
        selectedDriverId
    );


  const selectedRouting =
    selectedDriver
      ? routingStatusFor(
          selectedDriver.id
        )
      : undefined;


  const previewCurrent =
    (
      preview
      &&
      sameOrderIds(
        preview.selected_order_ids,
        selectedOrderIds
      )
      &&
      preview.driver_id
        ===
        Number(
          selectedDriverId
        )
    );


  return (
    <div
      style={{
        display:
          "grid",

        gap:
          20,
      }}
    >

      <div className="header">
        <div>

          <div className="eyebrow">
            StoreDash Operations
          </div>

          <h1>
            Dispatch
          </h1>

          <p className="label">
            Build one physical rider route.
            Orders are reserved while awaiting
            the driver response and assigned only after acceptance.
          </p>

        </div>

        <button
          className="btn btn-secondary"
          disabled={
            busy
          }
          onClick={() =>
            void refresh()
          }
        >
          Refresh
        </button>
      </div>


      {
        requestedOrderId
        != null
        && (
          <div className="card">

            <strong>
              Dispatching Order {
                requestedOrderId
              }
            </strong>

            <p
              className="label"
              style={{
                marginTop:
                  6,
              }}
            >
              This order was preselected.
              You may add other ready orders
              before the driver approves the route.
            </p>

          </div>
        )
      }


      {
        error
        && (
          <div className="card">
            <strong>
              {error}
            </strong>
          </div>
        )
      }


      {
        message
        && (
          <div className="card">
            {message}
          </div>
        )
      }


      <div className="card">

        <h2>
          1. Choose Rider
        </h2>

        <select
          value={
            selectedDriverId
          }
          disabled={
            busy
          }
          onChange={
            (event) => {

              setSelectedDriverId(
                event.target.value
              );

              setPreview(
                null
              );

              setError(
                ""
              );

              setMessage(
                ""
              );
            }
          }
          style={{
            marginTop:
              12,

            width:
              "100%",

            maxWidth:
              520,

            padding:
              10,
          }}
        >

          <option value="">
            Choose rider
          </option>

          {
            drivers
              .filter(
                (driver) =>
                  driver.is_active
              )
              .map(
                (driver) => {

                  const routing =
                    routingStatusFor(
                      driver.id
                    );


                  const ready =
                    driverReady(
                      driver
                    );


                  const status =
                    !driver.is_available
                      ? "Busy"
                      :
                      !routing
                        ?.routing_profile_complete
                        ? "Routing profile incomplete"
                        : "Ready";


                  return (
                    <option
                      key={
                        driver.id
                      }
                      value={
                        driver.id
                      }
                      disabled={
                        !ready
                      }
                    >
                      {
                        driver.name
                      }
                      {" · "}
                      {
                        driver.vehicle_type
                      }
                      {" · "}
                      {
                        status
                      }
                    </option>
                  );
                }
              )
          }

        </select>


        {
          selectedDriver
          &&
          selectedRouting
          && (
            <div
              className="label"
              style={{
                marginTop:
                  10,
              }}
            >
              {
                selectedRouting
                  .registration
                || "No registration"
              }
            </div>
          )
        }

      </div>


      <div className="card">

        <div
          style={{
            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "space-between",

            gap:
              12,

            flexWrap:
              "wrap",
          }}
        >

          <div>
            <h2>
              2. Choose Orders
            </h2>

            <p className="label">
              {
                selectedOrderIds.length
              } selected of {
                pool?.count
                || 0
              } ready orders.
            </p>
          </div>


          <div
            style={{
              display:
                "flex",

              gap:
                8,

              flexWrap:
                "wrap",
            }}
          >

            <button
              className="btn btn-secondary"
              disabled={
                busy
                ||
                !selectedOrderIds
                  .length
              }
              onClick={() => {

                setSelectedOrderIds(
                  []
                );

                setPreview(
                  null
                );

                setMessage(
                  ""
                );
              }}
            >
              Clear
            </button>


            <button
              className="btn"
              disabled={
                busy
                ||
                !selectedDriverId
                ||
                !pool?.count
              }
              onClick={
                autoPickOrders
              }
            >
              Auto Pick Orders
            </button>

          </div>

        </div>


        <div
          style={{
            display:
              "grid",

            gridTemplateColumns:
              "repeat(auto-fit, minmax(160px, 1fr))",

            gap:
              10,

            marginTop:
              16,
          }}
        >

          {
            pool?.order_ids
              .map(
                (orderId) => {

                  const checked =
                    selectedOrderIds
                      .includes(
                        orderId
                      );


                  return (
                    <label
                      key={
                        orderId
                      }
                      className="card"
                      style={{
                        display:
                          "flex",

                        alignItems:
                          "center",

                        gap:
                          10,

                        cursor:
                          busy
                            ? "default"
                            : "pointer",
                      }}
                    >

                      <input
                        type="checkbox"
                        checked={
                          checked
                        }
                        disabled={
                          busy
                        }
                        onChange={() =>
                          toggleOrder(
                            orderId
                          )
                        }
                      />

                      <strong>
                        Order {
                          orderId
                        }
                      </strong>

                    </label>
                  );
                }
              )
          }

        </div>


        {
          !pool?.count
          && (
            <p
              className="label"
              style={{
                marginTop:
                  14,
              }}
            >
              No paid orders are currently
              ready for dispatch.
            </p>
          )
        }

      </div>


      {
        selectedOrderIds.length > 0
        && (
          <div className="card">

            <h2>
              Selected Route Draft
            </h2>

            <p className="label">
              Orders {
                selectedOrderIds.join(
                  ", "
                )
              }
            </p>

            {
              previewing
              && (
                <p
                  style={{
                    marginTop:
                      12,
                  }}
                >
                  Recalculating route,
                  capacity and payout...
                </p>
              )
            }

            {
              !selectedDriverId
              && (
                <p
                  style={{
                    marginTop:
                      12,
                  }}
                >
                  Choose a rider to check
                  this route.
                </p>
              )
            }

          </div>
        )
      }


      {
        preview
        &&
        previewCurrent
        && (
          <div className="card">

            <h2>
              3. Driver Response
            </h2>

            <p className="label">
              Selecting orders only builds the route.
              The driver is not assigned until they accept.
            </p>

            {
              pendingDriverBatch
              &&
              pendingDriverOfferId
                != null
                ? (
                    <div
                      style={{
                        marginTop:
                          18,
                      }}
                    >

                      <strong>
                        AWAITING DRIVER RESPONSE
                      </strong>

                      <p
                        className="label"
                        style={{
                          marginTop:
                            8,
                        }}
                      >
                        Batch {
                          pendingDriverBatch.batch_id
                        } has been sent to the driver.
                      </p>

                      <div
                        style={{
                          display:
                            "flex",

                          gap:
                            10,

                          flexWrap:
                            "wrap",

                          marginTop:
                            14,
                        }}
                      >

                        <button
                          className="btn btn-secondary"
                          disabled={
                            busy
                          }
                          onClick={
                            markDriverDeclined
                          }
                        >
                          Driver Declined
                        </button>

                        <button
                          className="btn"
                          disabled={
                            busy
                          }
                          onClick={
                            acceptPendingDriver
                          }
                        >
                          {
                            busy
                              ? "Working..."
                              : "Driver Accepted — Dispatch"
                          }
                        </button>

                      </div>

                    </div>
                  )
                : (
                    <div
                      style={{
                        marginTop:
                          18,
                      }}
                    >

                      <p className="label">
                        {
                          selectedOrderIds.length === 0
                            ? "Choose at least one order."
                            : (
                                !selectedDriverId
                                  ? "Choose a driver."
                                  : (
                                      !previewCurrent
                                        ? "Waiting for route preview..."
                                        : (
                                            preview
                                            &&
                                            preview.plan.feasible
                                              ? "Route ready. Send it to the driver."
                                              : "Route is not feasible."
                                          )
                                    )
                              )
                        }
                      </p>

                      <button
                        className="btn"
                        style={{
                          marginTop:
                            12,
                        }}
                        disabled={
                          busy
                          ||
                          previewing
                          ||
                          !previewCurrent
                          ||
                          !preview
                          ||
                          !preview.plan.feasible
                          ||
                          !preview.pricing
                        }
                        onClick={
                          sendToDriver
                        }
                      >
                        {
                          busy
                            ? "Sending..."
                            : "Send Route to Driver"
                        }
                      </button>

                    </div>
                  )
            }

            <h2
              style={{
                marginTop:
                  28,
              }}
            >
              4. Route Preview
            </h2>


            <p className="label">
              {
                preview.vehicle
                  .manufacturer
              }
              {" "}
              {
                preview.vehicle
                  .model
              }
              {
                preview.vehicle
                  .variant
                  ? ` ${preview.vehicle.variant}`
                  : ""
              }
              {" · "}
              {
                preview.driver_name
              }
            </p>


            <div
              style={{
                display:
                  "grid",

                gridTemplateColumns:
                  "repeat(auto-fit, minmax(180px, 1fr))",

                gap:
                  14,

                marginTop:
                  18,
              }}
            >

              <div>
                <div className="label">
                  Safe payload
                </div>

                <strong>
                  {
                    preview.capacity
                      .max_payload_kg
                      .toFixed(
                        1
                      )
                  } kg
                </strong>
              </div>


              <div>
                <div className="label">
                  Safe volume
                </div>

                <strong>
                  {
                    preview.capacity
                      .max_volume_l
                      .toFixed(
                        1
                      )
                  } L
                </strong>
              </div>


              <div>
                <div className="label">
                  Selected orders
                </div>

                <strong>
                  {
                    preview.selected_order_ids
                      .length
                  }
                </strong>
              </div>

            </div>


            {
              !preview.plan.feasible
              ? (
                <div
                  style={{
                    marginTop:
                      20,
                  }}
                >

                  <h3>
                    Cannot assign this combination
                  </h3>

                  <p
                    style={{
                      marginTop:
                        8,
                    }}
                  >
                    {
                      humanizeReason(
                        preview.plan
                          .rejection_reason
                      )
                    }
                  </p>

                  <p
                    className="label"
                    style={{
                      marginTop:
                        8,
                    }}
                  >
                    Remove an order or choose
                    a rider with a larger verified
                    vehicle capacity.
                  </p>

                </div>
              )
              : (
                <>

                  <div
                    style={{
                      display:
                        "grid",

                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(160px, 1fr))",

                      gap:
                        14,

                      marginTop:
                        20,
                    }}
                  >

                    <div>
                      <div className="label">
                        Peak weight
                      </div>

                      <strong>
                        {
                          preview.plan
                            .peak_weight_kg
                            .toFixed(
                              1
                            )
                        } / {
                          preview.capacity
                            .max_payload_kg
                            .toFixed(
                              1
                            )
                        } kg
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Peak volume
                      </div>

                      <strong>
                        {
                          preview.plan
                            .peak_volume_l
                            .toFixed(
                              1
                            )
                        } / {
                          preview.capacity
                            .max_volume_l
                            .toFixed(
                              1
                            )
                        } L
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Pickups
                      </div>

                      <strong>
                        {
                          preview.plan
                            .pickup_count
                        }
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Deliveries
                      </div>

                      <strong>
                        {
                          preview.plan
                            .delivery_count
                        }
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Distance
                      </div>

                      <strong>
                        {
                          preview.plan
                            .total_distance_km
                            .toFixed(
                              1
                            )
                        } km
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Route time
                      </div>

                      <strong>
                        {
                          preview.plan
                            .total_route_minutes
                            .toFixed(
                              0
                            )
                        } min
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Delivery revenue
                      </div>

                      <strong>
                        GH₵{
                          preview.plan
                            .customer_delivery_revenue
                            .toFixed(
                              2
                            )
                        }
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Driver payout
                      </div>

                      <strong>
                        GH₵{
                          Number(
                            preview.pricing
                              ?.predicted_driver_payout
                            || 0
                          ).toFixed(
                            2
                          )
                        }
                      </strong>
                    </div>


                    <div>
                      <div className="label">
                        Contribution
                      </div>

                      <strong>
                        GH₵{
                          Number(
                            preview.pricing
                              ?.predicted_contribution
                            || 0
                          ).toFixed(
                            2
                          )
                        }
                      </strong>
                    </div>

                  </div>


                  <div
                    style={{
                      marginTop:
                        24,
                    }}
                  >

                    <h3>
                      Route Stops
                    </h3>


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

                      {
                        preview.plan
                          .stops.map(
                            (stop) => (
                              <div
                                key={
                                  stop.key
                                }
                                className="card"
                              >

                                <strong>
                                  {
                                    stop.sequence
                                  }. {
                                    stop.stop_type
                                  }
                                </strong>

                                <div className="label">
                                  {
                                    stop.location_label
                                    ||
                                    (
                                      stop.order_id
                                      != null
                                        ? `Order ${stop.order_id}`
                                        : "Route stop"
                                    )
                                  }
                                </div>

                                <div
                                  className="label"
                                  style={{
                                    marginTop:
                                      4,
                                  }}
                                >
                                  Load after stop: {
                                    stop.load_weight_after_kg
                                      .toFixed(
                                        1
                                      )
                                  } kg · {
                                    stop.load_volume_after_l
                                      .toFixed(
                                        1
                                      )
                                  } L
                                </div>

                              </div>
                            )
                          )
                      }

                    </div>
                  </div>


                  <div
                    style={{
                      display:
                        "flex",

                      gap:
                        10,

                      flexWrap:
                        "wrap",

                      marginTop:
                        24,
                    }}
                  >

                    <button
                      className="btn btn-secondary"
                      onClick={
                        markDriverDeclined
                      }
                      disabled={
                        busy
                        ||
                        previewing
                        ||
                        !pendingDriverBatch
                        ||
                        pendingDriverOfferId
                          == null
                      }
                    >
                      Driver Declined
                    </button>


                    <button
                      className="btn"
                      disabled={
                        busy
                        ||
                        previewing
                        ||
                        (
                          !pendingDriverBatch
                          &&
                          !previewCurrent
                        )
                      }
                      onClick={
                        pendingDriverBatch
                        &&
                        pendingDriverOfferId
                          != null
                          ? acceptPendingDriver
                          : sendToDriver
                      }
                    >
                      {
                        busy
                          ? "Working..."
                          : (
                              pendingDriverBatch
                              &&
                              pendingDriverOfferId
                                != null
                                ? "Driver Accepted — Dispatch"
                                : "Send Route to Driver"
                            )
                      }
                    </button>

                  </div>


                  <p
                    className="label"
                    style={{
                      marginTop:
                        12,
                    }}
                  >
                    {
                      pendingDriverBatch
                      &&
                      pendingDriverOfferId
                        != null
                        ? "AWAITING DRIVER RESPONSE — orders are reserved but not assigned until the driver accepts."
                        : "Review the route, then send it to the driver for approval."
                    }
                  </p>

                </>
              )
            }

          </div>
        )
      }

    </div>
  );
}
