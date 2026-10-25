"use client";

import Link from "next/link";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type Driver = {
  id: number;

  name: string;
  phone: string;

  vehicle_type: string;

  vehicle_registration:
    string | null;

  current_area:
    string | null;

  payment_phone:
    string | null;

  payment_name:
    string | null;

  notes:
    string | null;

  is_available: boolean;
  is_active: boolean;

  completion_rate: number;
};


type RoutingStatus = {
  driver_id: number;
  driver_name: string;

  is_active: boolean;
  is_available: boolean;

  routing_profile_complete:
    boolean;

  driver_vehicle_id:
    number | null;

  vehicle_spec_id:
    number | null;

  registration:
    string | null;

  reason:
    string | null;
};


const emptyRoutingFields = () => ({
  manufacturer: "",
  model: "",
  variant: "",

  max_payload_kg: "",
  cargo_volume_l: "",

  reference_km_per_liter:
    "",

  fuel_type:
    "",

  safe_capacity_ratio:
    "0.90",

  current_latitude:
    "",

  current_longitude:
    "",
});


type DeliveryOrder = {
  id: number;

  order_number: string;

  daily_number:
    number | null;

  status: string;

  delivery_fee: number;

  driver_payout:
    number | null;

  route_distance_km:
    number | null;

  route_duration_minutes:
    number | null;

  total_load_units:
    number | null;

  total_weight_kg:
    number | null;

  total_volume_l:
    number | null;

  customer: {
    id: number | null;

    name: string | null;

    owner_name:
      string | null;

    phone:
      string | null;

    alternate_phone:
      string | null;

    address:
      string | null;

    landmark:
      string | null;

    delivery_instructions:
      string | null;
  };

  driver: {
    id: number;

    name: string;

    phone: string;

    vehicle_type: string;

    vehicle_registration:
      string | null;

    current_area:
      string | null;
  } | null;
};


type Negotiation = {
  id: number;

  order_id: number;

  driver: {
    id: number;

    name: string;

    phone: string;

    vehicle_type: string;

    current_area:
      string | null;
  };

  driver_quote:
    number | null;

  authorized_offer:
    number | null;

  final_payout:
    number | null;

  counter_round: number;

  outcome: string;

  instruction: string;
};


export default function DriversPage() {

  // ========================================================
  // DRIVER NETWORK
  // ========================================================

  const [
    drivers,
    setDrivers,
  ] = useState<Driver[]>([]);


  // ========================================================
  // OPERATIONS
  // ========================================================

  const [
    dailyNumber,
    setDailyNumber,
  ] = useState("");


  const [
    selectedOrder,
    setSelectedOrder,
  ] = useState<
    DeliveryOrder | null
  >(null);


  const [
    selectedDriverId,
    setSelectedDriverId,
  ] = useState("");


  const [
    negotiation,
    setNegotiation,
  ] = useState<
    Negotiation | null
  >(null);


  const [
    driverQuote,
    setDriverQuote,
  ] = useState("");


  const [
    holdingDrivers,
    setHoldingDrivers,
  ] = useState<
    Negotiation[]
  >([]);


  const [
    active,
    setActive,
  ] = useState<
    DeliveryOrder[]
  >([]);


  const [
    completed,
    setCompleted,
  ] = useState<
    DeliveryOrder[]
  >([]);


  const [
    problems,
    setProblems,
  ] = useState<
    DeliveryOrder[]
  >([]);



  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  // ========================================================
  // ADD DRIVER
  // ========================================================

  const [
    savingDriver,
    setSavingDriver,
  ] = useState(false);


  const [
    form,
    setForm,
  ] = useState({
    name: "",
    phone: "",
    vehicle_type:
      "tricycle",

    vehicle_registration:
      "",

    current_area:
      "",

    payment_phone:
      "",

    payment_name:
      "",

    notes:
      "",

    ...emptyRoutingFields(),
  });


  const [
    routingStatuses,
    setRoutingStatuses,
  ] = useState<
    RoutingStatus[]
  >([]);


  const [
    profileDriverId,
    setProfileDriverId,
  ] = useState("");


  const [
    profileForm,
    setProfileForm,
  ] = useState(
    emptyRoutingFields()
  );


  const [
    savingProfile,
    setSavingProfile,
  ] = useState(false);


  const [
    profileMessage,
    setProfileMessage,
  ] = useState("");


  async function refreshAll() {

    try {

      const [
        driverData,
        activeData,
        completedData,
        routingData,
      ] = await Promise.all([

        api<Driver[]>(
          "/drivers?active_only=false"
        ),

        api<DeliveryOrder[]>(
          "/driver-operations/active"
        ),

        api<DeliveryOrder[]>(
          "/driver-operations/completed"
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


      if (!profileDriverId) {

        const firstIncomplete =
          routingData.find(
            (routing) =>
              routing.is_active
              &&
              !routing
                .routing_profile_complete
          );


        if (firstIncomplete) {

          setProfileDriverId(
            String(
              firstIncomplete
                .driver_id
            )
          );
        }
      }

      setActive(
        activeData
      );

      setCompleted(
        completedData
      );



      const problemData =
        await api<
          DeliveryOrder[]
        >(
          "/driver-operations/problems"
        );


      setProblems(
        problemData
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not load driver operations."
      );
    }
  }


  useEffect(() => {
    refreshAll();
  }, []);


  // ========================================================
  // FIND TODAY'S ORDER
  // ========================================================

  async function loadHoldingDrivers(
    orderId: number
  ) {
    try {
      const data =
        await api<
          Negotiation[]
        >(
          `/orders/${orderId}/driver-negotiation/holding`
        );

      setHoldingDrivers(
        data
      );

    } catch {
      setHoldingDrivers(
        []
      );
    }
  }


  async function findOrder(
    event: FormEvent
  ) {

    event.preventDefault();


    if (!dailyNumber) {
      return;
    }


    try {

      setLoading(
        true
      );

      setError("");

      setNegotiation(
        null
      );


      const order =
        await api<
          DeliveryOrder
        >(
          `/driver-operations/order/${dailyNumber}`
        );


      setSelectedOrder(
        order
      );




    } catch (error) {

      setSelectedOrder(
        null
      );

      setNegotiation(
        null
      );

      setError(
        error instanceof Error
          ? error.message
          : "Could not find order."
      );


    } finally {

      setLoading(
        false
      );
    }
  }


  // ========================================================
  // START DRIVER CALL
  // ========================================================

  async function startDriverCall() {

    if (
      !selectedOrder
      || !selectedDriverId
    ) {
      return;
    }


    try {

      setError("");


      const data =
        await api<
          Negotiation
        >(
          `/orders/${selectedOrder.id}/driver-negotiation/start`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                driver_id:
                  Number(
                    selectedDriverId
                  ),

                operator_id:
                  null,
              }),
          }
        );


      setNegotiation(
        data
      );

      setDriverQuote(
        ""
      );

      await loadHoldingDrivers(
        selectedOrder.id
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not start driver call."
      );
    }
  }


  // ========================================================
  // SUBMIT DRIVER'S PRICE
  // ========================================================

  async function submitDriverQuote(
    event: FormEvent
  ) {

    event.preventDefault();


    if (
      !selectedOrder
      || !negotiation
      || !driverQuote
    ) {
      return;
    }


    try {

      setError("");


      const data =
        await api<
          Negotiation
        >(
          `/orders/${selectedOrder.id}/driver-negotiation/${negotiation.id}/quote`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                amount:
                  Number(
                    driverQuote
                  ),

                operator_id:
                  null,
              }),
          }
        );


      setNegotiation(
        data
      );

      setDriverQuote(
        ""
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not submit driver quote."
      );
    }
  }


  // ========================================================
  // DRIVER ACCEPTS
  // ========================================================

  async function driverAccepted() {

    if (
      !selectedOrder
      || !negotiation
    ) {
      return;
    }


    try {

      const data =
        await api<
          Negotiation
        >(
          `/orders/${selectedOrder.id}/driver-negotiation/${negotiation.id}/accept`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                operator_id:
                  null,
              }),
          }
        );


      setNegotiation(
        data
      );


      const refreshed =
        await api<
          DeliveryOrder
        >(
          `/driver-operations/today/order/${selectedOrder.daily_number}`
        );


      setSelectedOrder(
        refreshed
      );


      await refreshAll();


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not assign driver."
      );
    }
  }


  // ========================================================
  // HELD DRIVER CALLS BACK AND ACCEPTS FINAL OFFER
  // ========================================================

  async function acceptHoldingDriver(
    held: Negotiation
  ) {

    if (!selectedOrder) {
      return;
    }

    try {
      setError("");

      const data =
        await api<
          Negotiation
        >(
          `/orders/${selectedOrder.id}/driver-negotiation/${held.id}/accept`,
          {
            method: "POST",

            body:
              JSON.stringify({
                operator_id:
                  null,
              }),
          }
        );

      setNegotiation(
        data
      );

      const refreshed =
        await api<
          DeliveryOrder
        >(
          `/driver-operations/today/order/${selectedOrder.daily_number}`
        );

      setSelectedOrder(
        refreshed
      );

      setHoldingDrivers(
        []
      );

      await refreshAll();

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not accept held driver."
      );
    }
  }


  // ========================================================
  // DRIVER UNAVAILABLE
  // ========================================================

  async function driverUnavailable() {

    if (
      !selectedOrder
      || !negotiation
    ) {
      return;
    }


    try {

      const data =
        await api<
          Negotiation
        >(
          `/orders/${selectedOrder.id}/driver-negotiation/${negotiation.id}/unavailable`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                operator_id:
                  null,
              }),
          }
        );


      setNegotiation(
        data
      );

      setSelectedDriverId(
        ""
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not update driver."
      );
    }
  }


  // ========================================================
  // DELIVERY STATUS
  // ========================================================

  async function deliveryAction(
    orderId: number,
    action: string,
    notes?: string,
  ) {

    try {

      await api(
        `/driver-operations/orders/${orderId}/status`,
        {
          method:
            "POST",

          body:
            JSON.stringify({
              action,

              operator_id:
                null,

              notes:
                notes
                || null,
            }),
        }
      );


      await refreshAll();


      if (
        selectedOrder
        && selectedOrder.id
        === orderId
        && selectedOrder.daily_number
      ) {

        const refreshed =
          await api<
            DeliveryOrder
          >(
            `/driver-operations/order/${selectedOrder.id}`
          );


        setSelectedOrder(
          refreshed
        );
      }


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not update delivery."
      );
    }
  }


  async function markDeliveryProblem(
    orderId: number
  ) {

    const reason =
      window.prompt(
        "Why was this order not delivered?"
      );


    if (
      reason == null
    ) {
      return;
    }


    if (
      !reason.trim()
    ) {

      setError(
        "Enter a reason for the delivery problem."
      );

      return;
    }


    await deliveryAction(
      orderId,
      "problem",
      reason.trim(),
    );
  }


  // ========================================================
  // CREATE DRIVER
  // ========================================================

  async function addDriver(
    event: FormEvent
  ) {

    event.preventDefault();


    try {

      setSavingDriver(
        true
      );

      setError("");

      setProfileMessage("");


      await api(
        "/drivers/onboard",
        {
          method:
            "POST",

          body:
            JSON.stringify({

              driver: {
                name:
                  form.name,

                phone:
                  form.phone,

                vehicle_type:
                  form.vehicle_type,

                vehicle_registration:
                  form.vehicle_registration
                  || null,

                current_area:
                  form.current_area
                  || null,

                latitude:
                  Number(
                    form.current_latitude
                  ),

                longitude:
                  Number(
                    form.current_longitude
                  ),

                payment_phone:
                  form.payment_phone
                  || null,

                payment_name:
                  form.payment_name
                  || null,

                notes:
                  form.notes
                  || null,

                is_available:
                  true,

                is_active:
                  true,
              },


              routing: {
                manufacturer:
                  form.manufacturer,

                model:
                  form.model,

                variant:
                  form.variant
                  || null,

                max_payload_kg:
                  Number(
                    form.max_payload_kg
                  ),

                cargo_volume_l:
                  Number(
                    form.cargo_volume_l
                  ),

                reference_km_per_liter:
                  form.reference_km_per_liter
                    ? Number(
                        form.reference_km_per_liter
                      )
                    : null,

                fuel_type:
                  form.fuel_type
                  || null,

                registration:
                  form.vehicle_registration
                  || null,

                safe_capacity_ratio:
                  Number(
                    form.safe_capacity_ratio
                  ),

                current_latitude:
                  Number(
                    form.current_latitude
                  ),

                current_longitude:
                  Number(
                    form.current_longitude
                  ),

                current_area:
                  form.current_area
                  || null,
              },
            }),
        }
      );


      setForm({
        name: "",
        phone: "",

        vehicle_type:
          "tricycle",

        vehicle_registration:
          "",

        current_area:
          "",

        payment_phone:
          "",

        payment_name:
          "",

        notes:
          "",

        ...emptyRoutingFields(),
      });


      setProfileMessage(
        "Driver created with a complete routing profile and is ready for Dispatch."
      );


      await refreshAll();


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not onboard driver."
      );


    } finally {

      setSavingDriver(
        false
      );
    }
  }


  async function completeRoutingProfile() {

    if (!profileDriverId) {

      setError(
        "Choose a driver whose routing profile needs completion."
      );

      return;
    }


    const driver =
      drivers.find(
        (item) =>
          item.id
          ===
          Number(
            profileDriverId
          )
      );


    if (!driver) {

      setError(
        "Driver not found."
      );

      return;
    }


    try {

      setSavingProfile(
        true
      );

      setError("");

      setProfileMessage("");


      await api(
        `/drivers/${driver.id}/routing-profile`,
        {
          method:
            "POST",

          body:
            JSON.stringify({
              manufacturer:
                profileForm.manufacturer,

              model:
                profileForm.model,

              variant:
                profileForm.variant
                || null,

              max_payload_kg:
                Number(
                  profileForm.max_payload_kg
                ),

              cargo_volume_l:
                Number(
                  profileForm.cargo_volume_l
                ),

              reference_km_per_liter:
                profileForm
                  .reference_km_per_liter
                    ? Number(
                        profileForm
                          .reference_km_per_liter
                      )
                    : null,

              fuel_type:
                profileForm.fuel_type
                || null,

              registration:
                driver
                  .vehicle_registration
                || null,

              safe_capacity_ratio:
                Number(
                  profileForm
                    .safe_capacity_ratio
                ),

              current_latitude:
                Number(
                  profileForm
                    .current_latitude
                ),

              current_longitude:
                Number(
                  profileForm
                    .current_longitude
                ),

              current_area:
                driver.current_area
                || null,
            }),
        }
      );


      setProfileForm(
        emptyRoutingFields()
      );


      setProfileDriverId(
        ""
      );


      setProfileMessage(
        `${driver.name} now has a complete routing profile and can be used in Dispatch.`
      );


      await refreshAll();


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not complete routing profile."
      );


    } finally {

      setSavingProfile(
        false
      );
    }
  }


  const incompleteDrivers =
    drivers.filter(
      (driver) =>
        driver.is_active
        &&
        routingStatuses.some(
          (routing) =>
            routing.driver_id
              === driver.id
            &&
            !routing
              .routing_profile_complete
        )
    );


  const availableDrivers =
    drivers.filter(
      (
        driver
      ) =>
        driver.is_active
        && driver.is_available
    );


  return (
    <div
      style={{
        display:
          "grid",

        gap:
          24,
      }}
    >

      {/* ================================================== */}
      {/* HEADER */}
      {/* ================================================== */}

      <div className="card">

        <h1>
          Driver Operations
        </h1>

        <p className="label">
          Manage the driver network and
          follow StoreDash deliveries.
          New rider assignments are handled
          from Dispatch.
        </p>

      </div>


      {/* ================================================== */}
      {/* FIND ORDER */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Find Delivery Order
        </h2>


        <form
          onSubmit={
            findOrder
          }
          style={{
            display:
              "flex",

            gap:
              10,

            marginTop:
              16,
          }}
        >

          <input
            type="number"
            min="1"

            placeholder="StoreDash Order ID"

            value={
              dailyNumber
            }

            onChange={
              (
                event
              ) =>
                setDailyNumber(
                  event.target.value
                )
            }
          />


          <button
            className="btn"
            disabled={
              loading
            }
          >
            {
              loading
                ? "Finding..."
                : "Find Order"
            }
          </button>

        </form>


        {
          selectedOrder
          && (
            <div
              style={{
                marginTop:
                  20,

                borderTop:
                  "1px solid #e5e7eb",

                paddingTop:
                  18,
              }}
            >

              <h3>
                Order #
                {
                  selectedOrder.daily_number
                }
              </h3>


              <div className="label">
                {
                  selectedOrder.order_number
                }
                {" · "}
                {
                  selectedOrder.status
                    .replaceAll(
                      "_",
                      " "
                    )
                }
              </div>


              <div
                style={{
                  marginTop:
                    14,

                  display:
                    "grid",

                  gap:
                    5,
                }}
              >

                <div>
                  <strong>
                    Customer:
                  </strong>{" "}
                  {
                    selectedOrder
                      .customer
                      .name
                    || "Unknown"
                  }
                </div>


                <div>
                  <strong>
                    Delivery:
                  </strong>{" "}
                  {
                    selectedOrder
                      .customer
                      .address
                    || "No address"
                  }
                </div>


                {
                  selectedOrder
                    .customer
                    .landmark
                  && (
                    <div>
                      <strong>
                        Landmark:
                      </strong>{" "}
                      {
                        selectedOrder
                          .customer
                          .landmark
                      }
                    </div>
                  )
                }


                <div>
                  <strong>
                    Route:
                  </strong>{" "}
                  {
                    selectedOrder
                      .route_distance_km
                    ?? "-"
                  }
                  {" km · "}
                  {
                    selectedOrder
                      .route_duration_minutes
                    ?? "-"
                  }
                  {" min"}
                </div>


                <div>
                  <strong>
                    Cargo:
                  </strong>{" "}
                  {
                    selectedOrder
                      .total_weight_kg
                    ?? "-"
                  }
                  {" kg · "}
                  {
                    selectedOrder
                      .total_volume_l
                    ?? "-"
                  }
                  {" L"}
                </div>

              </div>


              {
                !selectedOrder.driver
                && (
                  !negotiation
                  || negotiation.outcome === "holding"
                  || negotiation.outcome === "unavailable"
                )
                && (
                  <div
                    style={{
                      marginTop:
                        20,
                    }}
                  >

                    <h3>
                      {
                        negotiation
                        && (
                          negotiation.outcome === "holding"
                          || negotiation.outcome === "unavailable"
                        )
                          ? "Choose Another Driver"
                          : "Select Driver"
                      }
                    </h3>


                    {
                      negotiation
                      && negotiation.outcome === "holding"
                      && (
                        <p className="label">
                          The previous driver could not
                          be agreed with. This order is
                          still open for another driver.
                        </p>
                      )
                    }


                    {
                      negotiation
                      && negotiation.outcome === "unavailable"
                      && (
                        <p className="label">
                          The previous driver is unavailable.
                          Choose another available driver.
                        </p>
                      )
                    }


                    <select
                      value={
                        selectedDriverId
                      }

                      onChange={
                        (
                          event
                        ) =>
                          setSelectedDriverId(
                            event.target.value
                          )
                      }

                      style={{
                        width:
                          "100%",

                        marginTop:
                          8,
                      }}
                    >

                      <option value="">
                        Select available driver
                      </option>


                      {
                        availableDrivers.map(
                          (
                            driver
                          ) => (
                            <option
                              key={
                                driver.id
                              }

                              value={
                                driver.id
                              }
                            >
                              {
                                driver.name
                              }
                              {" · "}
                              {
                                driver.vehicle_type
                              }
                              {
                                driver.current_area
                                  ? ` · ${driver.current_area}`
                                  : ""
                              }
                            </option>
                          )
                        )
                      }

                    </select>


                    <button
                      className="btn"

                      style={{
                        marginTop:
                          12,
                      }}

                      disabled={
                        !selectedDriverId
                      }

                      onClick={
                        startDriverCall
                      }
                    >
                      Start Driver Call
                    </button>

                  </div>
                )
              }


              {/* ========================================== */}
              {/* NEGOTIATION */}
              {/* ========================================== */}

              {
                negotiation
                && negotiation.outcome
                !== "accepted"
                && (
                  <div
                    style={{
                      marginTop:
                        22,

                      paddingTop:
                        18,

                      borderTop:
                        "1px solid #e5e7eb",
                    }}
                  >

                    <h3>
                      Driver Call
                    </h3>


                    <div>
                      <strong>
                        {
                          negotiation
                            .driver
                            .name
                        }
                      </strong>
                    </div>


                    <div className="label">
                      {
                        negotiation
                          .driver
                          .phone
                      }
                    </div>


                    <p
                      style={{
                        marginTop:
                          12,
                      }}
                    >
                      {
                        negotiation
                          .instruction
                      }
                    </p>


                    {
                      negotiation
                        .authorized_offer
                        !== null
                      && (
                        <div
                          style={{
                            marginTop:
                              14,
                          }}
                        >
                          <strong>
                            Authorized offer:
                            {" "}
                            GH₵
                            {
                              negotiation
                                .authorized_offer
                                .toFixed(
                                  2
                                )
                            }
                          </strong>
                        </div>
                      )
                    }


                    {
                      (
                        negotiation.outcome
                        === "pending"

                        || negotiation.outcome
                        === "countered"
                      )
                      && (
                        <form
                          onSubmit={
                            submitDriverQuote
                          }

                          style={{
                            marginTop:
                              16,

                            display:
                              "flex",

                            gap:
                              10,
                          }}
                        >

                          <input
                            type="number"
                            min="0.01"
                            step="0.01"

                            placeholder={
                              negotiation.outcome
                              === "pending"

                                ? "Driver's price"

                                : "Driver's new price"
                            }

                            value={
                              driverQuote
                            }

                            onChange={
                              (
                                event
                              ) =>
                                setDriverQuote(
                                  event.target.value
                                )
                            }
                          />


                          <button
                            className="btn"
                          >
                            Submit Price
                          </button>

                        </form>
                      )
                    }


                    {
                      (
                        negotiation.outcome
                        === "quote_authorized"

                        || negotiation.outcome
                        === "countered"
                      )
                      && negotiation
                        .authorized_offer
                        !== null
                      && (
                        <button
                          className="btn"

                          style={{
                            marginTop:
                              14,
                          }}

                          onClick={
                            driverAccepted
                          }
                        >
                          Driver Accepted
                          {" GH₵"}
                          {
                            negotiation
                              .authorized_offer
                              .toFixed(
                                2
                              )
                          }
                        </button>
                      )
                    }


                    {
                      negotiation.outcome
                      !== "stopped"
                      && (
                        <button
                          className="btn"

                          style={{
                            marginTop:
                              10,

                            marginLeft:
                              8,
                          }}

                          onClick={
                            driverUnavailable
                          }
                        >
                          Driver Unavailable
                        </button>
                      )
                    }


                    {
                      negotiation.outcome
                      === "stopped"
                      && (
                        <div
                          className="error"

                          style={{
                            marginTop:
                              14,
                          }}
                        >
                          This is StoreDash's final offer.
                          The driver is now on hold.
                          You can call another driver,
                          or accept them if they call back.
                        </div>
                      )
                    }

                  </div>
                )
              }


              {
                selectedOrder.driver
                && (
                  <div
                    style={{
                      marginTop:
                        20,
                    }}
                  >

                    <strong>
                      Assigned:
                      {" "}
                      {
                        selectedOrder
                          .driver
                          .name
                      }
                    </strong>

                    <div className="label">
                      Locked payout:
                      {" GH₵"}
                      {
                        selectedOrder
                          .driver_payout
                        ?.toFixed(
                          2
                        )
                        ?? "-"
                      }
                    </div>

                  </div>
                )
              }

            </div>
          )
        }

      </div>


      {/* ================================================== */}
      {/* DRIVERS ON HOLD */}
      {/* ================================================== */}

      {
        selectedOrder
        && !selectedOrder.driver
        && holdingDrivers.length > 0
        && (
          <div className="card">

            <h2>
              Drivers On Hold
            </h2>

            <p className="label">
              These drivers rejected StoreDash's
              final offer but may call back and
              accept while this order remains open.
            </p>

            <div
              style={{
                display: "grid",
                gap: 12,
                marginTop: 16,
              }}
            >
              {
                holdingDrivers.map(
                  (
                    held
                  ) => (
                    <div
                      key={
                        held.id
                      }

                      style={{
                        border:
                          "1px solid #e5e7eb",

                        borderRadius:
                          10,

                        padding:
                          14,
                      }}
                    >

                      <strong>
                        {
                          held.driver.name
                        }
                      </strong>

                      <div className="label">
                        {
                          held.driver.phone
                        }
                        {" · "}
                        {
                          held.driver.vehicle_type
                        }
                      </div>

                      <div
                        style={{
                          marginTop:
                            10,
                        }}
                      >
                        Final StoreDash offer:
                        {" "}
                        <strong>
                          GH₵
                          {
                            held.authorized_offer
                              ?.toFixed(
                                2
                              )
                            ?? "-"
                          }
                        </strong>
                      </div>

                      <p className="label">
                        If this driver calls back
                        and agrees to the final amount,
                        accept them here.
                      </p>

                      <button
                        className="btn"

                        disabled={
                          held.authorized_offer
                          === null
                        }

                        onClick={() =>
                          acceptHoldingDriver(
                            held
                          )
                        }
                      >
                        Driver Called Back —
                        Accept Final Offer
                      </button>

                    </div>
                  )
                )
              }
            </div>

          </div>
        )
      }


      {/* ================================================== */}
      {/* ACTIVE DELIVERIES */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Active Deliveries
        </h2>


        {
          active.length
          === 0
          ? (
            <p className="label">
              No active deliveries.
            </p>
          )
          : (
            <div
              style={{
                display:
                  "grid",

                gap:
                  14,

                marginTop:
                  16,
              }}
            >

              {
                active.map(
                  (
                    order
                  ) => (
                    <div
                      key={
                        order.id
                      }

                      style={{
                        padding:
                          14,

                        border:
                          "1px solid #e5e7eb",

                        borderRadius:
                          10,
                      }}
                    >

                      <strong>
                        Order #
                        {
                          order.daily_number
                        }
                      </strong>


                      <div className="label">
                        {
                          order.status
                            .replaceAll(
                              "_",
                              " "
                            )
                        }
                      </div>


                      <div
                        style={{
                          marginTop:
                            10,
                        }}
                      >

                        <div>
                          Driver:
                          {" "}
                          <strong>
                            {
                              order.driver
                                ?.name
                              || "-"
                            }
                          </strong>
                        </div>


                        <div>
                          Customer:
                          {" "}
                          {
                            order.customer
                              .name
                          }
                        </div>


                        <div>
                          Delivery:
                          {" "}
                          {
                            order.customer
                              .address
                          }
                        </div>


                        {
                          order.customer
                            .landmark
                          && (
                            <div>
                              Landmark:
                              {" "}
                              {
                                order.customer
                                  .landmark
                              }
                            </div>
                          )
                        }

                      </div>


                      <div
                        style={{
                          marginTop:
                            14,

                          display:
                            "flex",

                          gap:
                            8,

                          flexWrap:
                            "wrap",
                        }}
                      >

                        {
                          order.status
                          === "driver_assigned"
                          && (
                            <button
                              className="btn"

                              onClick={() =>
                                deliveryAction(
                                  order.id,
                                  "start_pickup"
                                )
                              }
                            >
                              Start Pickup
                            </button>
                          )
                        }


                        {
                          (
                            order.status
                            === "driver_assigned"

                            || order.status
                            === "pickup_in_progress"
                          )
                          && (
                            <button
                              className="btn"

                              onClick={() =>
                                deliveryAction(
                                  order.id,
                                  "out_for_delivery"
                                )
                              }
                            >
                              Out for Delivery
                            </button>
                          )
                        }


                        {
                          order.status
                          === "out_for_delivery"
                          && order.customer
                            .phone
                          && (
                            <a
                              className="btn"

                              href={
                                `tel:${order.customer.phone}`
                              }
                            >
                              Call Customer
                            </a>
                          )
                        }


                        {
                          order.status
                          === "out_for_delivery"
                          && (
                            <>
                              <button
                                className="btn"

                                onClick={() =>
                                  deliveryAction(
                                    order.id,
                                    "deliver_and_complete"
                                  )
                                }
                              >
                                Delivered — Finish Order
                              </button>

                              <button
                                className="btn btn-secondary"

                                onClick={() =>
                                  markDeliveryProblem(
                                    order.id
                                  )
                                }
                              >
                                Not Delivered / Problem
                              </button>
                            </>
                          )
                        }

                      </div>

                    </div>
                  )
                )
              }

            </div>
          )
        }

      </div>


      {/* ================================================== */}
      {/* DELIVERY PROBLEMS */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Needs Resolution
        </h2>

        {
          problems.length
          === 0
          ? (
            <p className="label">
              No unresolved delivery problems.
            </p>
          )
          : (
            <div
              style={{
                display:
                  "grid",

                gap:
                  12,

                marginTop:
                  16,
              }}
            >
              {
                problems.map(
                  (order) => (
                    <div
                      key={
                        order.id
                      }

                      style={{
                        padding:
                          14,

                        border:
                          "1px solid #e5e7eb",

                        borderRadius:
                          10,
                      }}
                    >
                      <strong>
                        Order ID {
                          order.id
                        }
                      </strong>

                      <div className="label">
                        Customer: {
                          order.customer.name
                        }
                      </div>

                      <div className="label">
                        Driver: {
                          order.driver
                            ?.name
                          || "-"
                        }
                      </div>

                      <div
                        style={{
                          display:
                            "flex",

                          gap:
                            8,

                          flexWrap:
                            "wrap",

                          marginTop:
                            12,
                        }}
                      >
                        {
                          order.customer.phone
                          && (
                            <a
                              className="btn btn-secondary"

                              href={
                                `tel:${order.customer.phone}`
                              }
                            >
                              Call Customer
                            </a>
                          )
                        }

                        <button
                          className="btn"

                          onClick={() =>
                            deliveryAction(
                              order.id,
                              "retry_delivery"
                            )
                          }
                        >
                          Retry Delivery
                        </button>
                      </div>
                    </div>
                  )
                )
              }
            </div>
          )
        }

      </div>


      {/* ================================================== */}
      {/* COMPLETED */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Completed / Delivered Today
        </h2>


        {
          completed.length
          === 0
          ? (
            <p className="label">
              No completed deliveries yet.
            </p>
          )
          : completed.map(
              (
                order
              ) => (
                <div
                  key={
                    order.id
                  }

                  style={{
                    marginTop:
                      12,

                    padding:
                      12,

                    border:
                      "1px solid #e5e7eb",

                    borderRadius:
                      10,
                  }}
                >

                  <strong>
                    Order #
                    {
                      order.daily_number
                    }
                  </strong>

                  <div className="label">
                    Driver: {
                      order.driver
                        ?.name
                      || "-"
                    }
                  </div>

                </div>
              )
            )
        }

      </div>


      {
        incompleteDrivers.length > 0
        && (
          <div className="card">

            <h2>
              Complete Routing Profile
            </h2>

            <p className="label">
              These riders already exist,
              but cannot be dispatched until
              their exact vehicle capacity and
              current routing location are configured.
            </p>


            <select
              required

              value={
                profileDriverId
              }

              onChange={
                (event) =>
                  setProfileDriverId(
                    event.target.value
                  )
              }
            >

              <option value="">
                Choose incomplete driver
              </option>

              {
                incompleteDrivers.map(
                  (driver) => (
                    <option
                      key={
                        driver.id
                      }

                      value={
                        driver.id
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
                        driver
                          .vehicle_registration
                        || "No registration"
                      }
                    </option>
                  )
                )
              }

            </select>


            <div
              style={{
                display:
                  "grid",

                gridTemplateColumns:
                  "repeat(auto-fit, minmax(220px, 1fr))",

                gap:
                  10,

                marginTop:
                  14,
              }}
            >

              <input
                required
                placeholder="Vehicle manufacturer"

                value={
                  profileForm.manufacturer
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      manufacturer:
                        event.target.value,
                    })
                }
              />


              <input
                required
                placeholder="Exact vehicle model"

                value={
                  profileForm.model
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      model:
                        event.target.value,
                    })
                }
              />


              <input
                placeholder="Variant / trim (optional)"

                value={
                  profileForm.variant
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      variant:
                        event.target.value,
                    })
                }
              />


              <input
                required
                type="number"
                min="0.01"
                step="any"
                placeholder="Verified max payload (kg)"

                value={
                  profileForm.max_payload_kg
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      max_payload_kg:
                        event.target.value,
                    })
                }
              />


              <input
                required
                type="number"
                min="0.01"
                step="any"
                placeholder="Usable cargo volume (L)"

                value={
                  profileForm.cargo_volume_l
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      cargo_volume_l:
                        event.target.value,
                    })
                }
              />


              <input
                type="number"
                min="0.01"
                step="any"
                placeholder="Reference km/L (optional)"

                value={
                  profileForm.reference_km_per_liter
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      reference_km_per_liter:
                        event.target.value,
                    })
                }
              />


              <input
                placeholder="Fuel type (optional)"

                value={
                  profileForm.fuel_type
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      fuel_type:
                        event.target.value,
                    })
                }
              />


              <input
                required
                type="number"
                min="0.01"
                max="1"
                step="0.01"
                placeholder="Safe capacity ratio"

                value={
                  profileForm.safe_capacity_ratio
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      safe_capacity_ratio:
                        event.target.value,
                    })
                }
              />


              <input
                required
                type="number"
                min="-90"
                max="90"
                step="any"
                placeholder="Current latitude"

                value={
                  profileForm.current_latitude
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      current_latitude:
                        event.target.value,
                    })
                }
              />


              <input
                required
                type="number"
                min="-180"
                max="180"
                step="any"
                placeholder="Current longitude"

                value={
                  profileForm.current_longitude
                }

                onChange={
                  (event) =>
                    setProfileForm({
                      ...profileForm,

                      current_longitude:
                        event.target.value,
                    })
                }
              />

            </div>


            <button
              className="btn"

              style={{
                marginTop:
                  14,
              }}

              disabled={
                savingProfile
                ||
                !profileDriverId
                ||
                !profileForm.manufacturer
                ||
                !profileForm.model
                ||
                !profileForm.max_payload_kg
                ||
                !profileForm.cargo_volume_l
                ||
                !profileForm.current_latitude
                ||
                !profileForm.current_longitude
              }

              onClick={
                () =>
                  void completeRoutingProfile()
              }
            >
              {
                savingProfile
                  ? "Saving Routing Profile..."
                  : "Complete Routing Profile"
              }
            </button>

          </div>
        )
      }


      {
        profileMessage
        && (
          <div className="card">
            {
              profileMessage
            }
          </div>
        )
      }


      {/* ================================================== */}
      {/* ADD DRIVER */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Add Driver
        </h2>


        <form
          onSubmit={
            addDriver
          }

          style={{
            display:
              "grid",

            gap:
              12,

            marginTop:
              16,
          }}
        >

          <input
            required

            placeholder="Driver name"

            value={
              form.name
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  name:
                    event.target.value,
                })
            }
          />


          <input
            required

            placeholder="Phone"

            value={
              form.phone
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  phone:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="What do they drive?"

            value={
              form.vehicle_type
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  vehicle_type:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Vehicle registration"

            value={
              form.vehicle_registration
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  vehicle_registration:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Current area"

            value={
              form.current_area
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  current_area:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Payout / MoMo phone"

            value={
              form.payment_phone
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  payment_phone:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Payout account name"

            value={
              form.payment_name
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  payment_name:
                    event.target.value,
                })
            }
          />


          <textarea
            placeholder="Notes"

            value={
              form.notes
            }

            onChange={
              (
                event
              ) =>
                setForm({
                  ...form,

                  notes:
                    event.target.value,
                })
            }
          />


          <div
            style={{
              marginTop:
                8,

              paddingTop:
                12,

              borderTop:
                "1px solid rgba(127,127,127,.25)",
            }}
          >

            <h3>
              Routing Vehicle Profile
            </h3>

            <p className="label">
              Required so this rider is usable
              in Dispatch immediately after creation.
              Use verified vehicle values — StoreDash
              will not invent capacity from the vehicle type.
            </p>

          </div>


          <input
            required
            placeholder="Vehicle manufacturer"

            value={
              form.manufacturer
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  manufacturer:
                    event.target.value,
                })
            }
          />


          <input
            required
            placeholder="Exact vehicle model"

            value={
              form.model
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  model:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Variant / trim (optional)"

            value={
              form.variant
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  variant:
                    event.target.value,
                })
            }
          />


          <input
            required
            type="number"
            min="0.01"
            step="any"
            placeholder="Verified max payload (kg)"

            value={
              form.max_payload_kg
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  max_payload_kg:
                    event.target.value,
                })
            }
          />


          <input
            required
            type="number"
            min="0.01"
            step="any"
            placeholder="Usable cargo volume (L)"

            value={
              form.cargo_volume_l
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  cargo_volume_l:
                    event.target.value,
                })
            }
          />


          <input
            type="number"
            min="0.01"
            step="any"
            placeholder="Reference km/L (optional)"

            value={
              form.reference_km_per_liter
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  reference_km_per_liter:
                    event.target.value,
                })
            }
          />


          <input
            placeholder="Fuel type (optional)"

            value={
              form.fuel_type
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  fuel_type:
                    event.target.value,
                })
            }
          />


          <input
            required
            type="number"
            min="0.01"
            max="1"
            step="0.01"
            placeholder="Safe capacity ratio"

            value={
              form.safe_capacity_ratio
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  safe_capacity_ratio:
                    event.target.value,
                })
            }
          />


          <input
            required
            type="number"
            min="-90"
            max="90"
            step="any"
            placeholder="Current latitude"

            value={
              form.current_latitude
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  current_latitude:
                    event.target.value,
                })
            }
          />


          <input
            required
            type="number"
            min="-180"
            max="180"
            step="any"
            placeholder="Current longitude"

            value={
              form.current_longitude
            }

            onChange={
              (event) =>
                setForm({
                  ...form,

                  current_longitude:
                    event.target.value,
                })
            }
          />


          <button
            className="btn"

            disabled={
              savingDriver
            }
          >
            {
              savingDriver
                ? "Saving..."
                : "Add Driver"
            }
          </button>

        </form>

      </div>


      {/* ================================================== */}
      {/* DRIVER NETWORK */}
      {/* ================================================== */}

      <div className="card">

        <h2>
          Driver Network
        </h2>


        <div
          style={{
            display:
              "grid",

            gap:
              12,

            marginTop:
              16,
          }}
        >

          {
            drivers.map(
              (
                driver
              ) => (
                <div
                  key={
                    driver.id
                  }

                  style={{
                    padding:
                      12,

                    border:
                      "1px solid #e5e7eb",

                    borderRadius:
                      10,
                  }}
                >

                  <div>
                    <strong>
                      {driver.name}
                    </strong>

                    <div>
                      <Link
                        href={`/drivers/${driver.id}`}
                        className="text-link"
                      >
                        View History →
                      </Link>
                    </div>
                  </div>

                  <div className="label">
                    {
                      driver.phone
                    }
                    {" · "}
                    {
                      driver.vehicle_type
                    }
                  </div>


                  <div className="label">
                    {
                      driver.is_available
                        ? "Available"
                        : "Busy / unavailable"
                    }
                  </div>

                </div>
              )
            )
          }

        </div>

      </div>


      {
        error
        && (
          <div className="error">
            {error}
          </div>
        )
      }

    </div>
  );
}
