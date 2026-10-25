"use client";

import Link from "next/link";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  useParams,
  useRouter,
} from "next/navigation";

import { api } from "@/lib/api";
import {
  setAutosaveState,
  waitForAutosaves,
} from "@/lib/autosave";

import OrderItemLogistics from "@/components/OrderItemLogistics";
import OrderLoadSummary from "@/components/OrderLoadSummary";
import type {
  Business,
} from "@/lib/types";


type WorkflowItem = {
  id: number;

  name: string;

  brand: string | null;

  size: string | null;

  requested_quantity: number;

  unit: string;

  confirmed_quantity:
    number | null;

  confirmed_price:
    number | string | null;

  supplier_id:
    number | null;

  availability_status:
    string;

  substitution_notes?:
    string | null;

  logistics_category_id?:
    number | null;

  logistics_type_id?:
    number | null;

  logistics_size_class?:
    string | null;

  load_units_each?:
    number | null;

  total_load_units?:
    number | null;


  logistics_variant_key?:
    string | null;

  logistics_size_detail?:
    string | null;

  physical_material_class?:
    string | null;

  physical_estimation_source?:
    string | null;

  physical_confidence?:
    number | null;

  weight_kg_each?:
    number | null;

  volume_l_each?:
    number | null;

  handling_score_each?:
    number | null;

  fragility_score_each?:
    number | null;

  total_weight_kg?:
    number | null;

  total_volume_l?:
    number | null;
};


type WorkflowOrder = {
  id: number;

  order_number: string;

  daily_number:
    number | null;

  operating_day_id:
    number | null;

  business_id: number;

  operator_id:
    number | null;

  status: string;

  notes:
    string | null;

  goods_total:
    number | string;

  delivery_fee:
    number | string;

  service_fee:
    number | string;

  final_total:
    number | string;

  tax_total?:
    number | string | null;

  route_distance_km?:
    number | null;

  route_duration_minutes?:
    number | null;

  supplier_stop_count?:
    number | null;

  total_load_units?:
    number | null;

  driver_floor?:
    number | string | null;

  driver_target?:
    number | string | null;

  driver_ceiling?:
    number | string | null;

  pricing_version?:
    string | null;

  created_at: string;

  quote_generated_at:
    string | null;

  customer_approved_at:
    string | null;

  payment_amount?:
    number | string | null;

  payment_method?:
    string | null;

  payment_reference?:
    string | null;

  payment_confirmed_at?:
    string | null;

  preparation_started_at?:
    string | null;

  ready_for_dispatch_at?:
    string | null;

  finalized_at:
    string | null;

  completed_at:
    string | null;

  items:
    WorkflowItem[];
};


type PairedSupplier = {
  relationship_id: number;

  supplier_id: number;

  supplier_number: string;

  name: string;

  category:
    string | null;

  phone: string;

  contact_person:
    string | null;

  location:
    string | null;

  is_usual: boolean;

  notes:
    string | null;
};


type EditableItem = {
  name: string;

  requested_quantity:
    number;

  unit: string;
};


const preFinalStatuses = [
  "draft",
  "sourcing",
  "quote_ready",
  "awaiting_buyer_approval",
];


export default function OrderWorkspacePage() {
  const params =
    useParams<{
      id: string;
    }>();


  const router =
    useRouter();


  const [
    order,
    setOrder,
  ] = useState<
    WorkflowOrder | null
  >(null);


  const [
    customer,
    setCustomer,
  ] = useState<
    Business | null
  >(null);


  const [
    suppliers,
    setSuppliers,
  ] = useState<
    PairedSupplier[]
  >([]);


  const [
    editableItems,
    setEditableItems,
  ] = useState<
    EditableItem[]
  >([]);


  const [
    notes,
    setNotes,
  ] = useState("");


  const [
    message,
    setMessage,
  ] = useState("");


  const [
    error,
    setError,
  ] = useState("");


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    paymentMethod,
    setPaymentMethod,
  ] = useState("momo");


  const [
    paymentReference,
    setPaymentReference,
  ] = useState("");


  const [
    paymentNotes,
    setPaymentNotes,
  ] = useState("");


  async function loadOrder() {
    try {
      setLoading(
        true
      );


      const orderData =
        await api<
          WorkflowOrder
        >(
          `/orders/${params.id}`
        );


      const [
        customerData,
        supplierData,
      ] = await Promise.all([
        api<Business>(
          `/businesses/${orderData.business_id}`
        ),

        api<PairedSupplier[]>(
          `/businesses/${orderData.business_id}/suppliers`
        ),
      ]);


      setOrder(
        orderData
      );


      setCustomer(
        customerData
      );


      setSuppliers(
        supplierData
      );


      setEditableItems(
        orderData.items.map(
          (item) => ({
            name:
              item.name,

            requested_quantity:
              item.requested_quantity,

            unit:
              item.unit,
          })
        )
      );


      setNotes(
        orderData.notes ||
        ""
      );



      setError(
        ""
      );


    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not load order."
      );

    } finally {
      setLoading(
        false
      );
    }
  }


  useEffect(() => {
    if (params.id) {
      loadOrder();
    }

  }, [params.id]);


  const editable =
    order
      ? preFinalStatuses.includes(
          order.status
        )
      : false;


  function updateEditableItem(
    index: number,
    key: keyof EditableItem,
    value: string | number
  ) {
    setEditableItems(
      (current) =>
        current.map(
          (
            item,
            currentIndex
          ) =>
            currentIndex ===
            index
              ? {
                  ...item,
                  [key]:
                    value,
                }
              : item
        )
    );
  }


  async function saveDraft() {
    if (!order) {
      return;
    }


    const valid =
      editableItems.filter(
        (item) =>
          item.name.trim() &&
          item.requested_quantity >
            0
      );


    if (!valid.length) {
      setError(
        "Order must contain at least one item."
      );

      return;
    }


    try {
      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/draft`,
          {
            method:
              "PUT",

            body:
              JSON.stringify({
                notes,

                items:
                  valid,
              }),
          }
        );


      setOrder(
        updated
      );


      setMessage(
        "Draft saved. Sourcing was reset because the requested order changed."
      );


      setError(
        ""
      );


      await loadOrder();


    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not save draft."
      );
    }
  }


  const [
    sourcingSaveState,
    setSourcingSaveState,
  ] = useState<
    Record<
      number,
      | "idle"
      | "saving"
      | "saved"
      | "error"
    >
  >({});


  const sourcingTimersRef =
    useRef<
      Record<
        number,
        ReturnType<
          typeof setTimeout
        >
      >
    >({});


  const sourcingChainsRef =
    useRef<
      Record<
        number,
        Promise<void>
      >
    >({});


  const sourcingLatestRef =
    useRef<
      Record<
        number,
        WorkflowItem
      >
    >({});


  const sourcingVersionRef =
    useRef<
      Record<
        number,
        number
      >
    >({});


  function sourcingAutosaveKey(
    itemId: number
  ) {
    return (
      `order:${params.id}:`
      + `sourcing:${itemId}`
    );
  }


  function setSourcingState(
    itemId: number,
    state:
      | "saving"
      | "saved"
      | "error",
    errorMessage?: string,
  ) {

    setSourcingSaveState(
      (current) => ({
        ...current,
        [itemId]:
          state,
      })
    );


    setAutosaveState(
      sourcingAutosaveKey(
        itemId
      ),
      state,
      errorMessage,
    );
  }


  function enqueueSourcingSave(
    itemId: number
  ): Promise<void> {

    if (!order) {
      return Promise.resolve();
    }


    const snapshot =
      sourcingLatestRef
        .current[
          itemId
        ];


    const version =
      sourcingVersionRef
        .current[
          itemId
        ];


    if (!snapshot) {
      return Promise.resolve();
    }


    const previous =
      sourcingChainsRef
        .current[
          itemId
        ]
      || Promise.resolve();


    const next =
      previous
        .catch(
          () => undefined
        )
        .then(
          async () => {

            let saved =
              false;

            let finalError:
              unknown = null;


            for (
              let attempt = 0;
              attempt < 2;
              attempt += 1
            ) {

              try {

                await api<
                  WorkflowOrder
                >(
                  `/orders/${order.id}/items/${itemId}/sourcing`,
                  {
                    method:
                      "PUT",

                    body:
                      JSON.stringify({
                        supplier_id:
                          snapshot
                            .supplier_id,

                        availability_status:
                          snapshot
                            .availability_status,

                        confirmed_quantity:
                          snapshot
                            .confirmed_quantity,

                        confirmed_price:
                          snapshot
                              .confirmed_price
                            === null
                          ||
                          snapshot
                              .confirmed_price
                            === ""
                            ? null
                            : Number(
                                snapshot
                                  .confirmed_price
                              ),

                        substitution_notes:
                          snapshot
                            .substitution_notes
                          || null,
                      }),
                  }
                );


                saved =
                  true;

                break;


              } catch (error) {

                finalError =
                  error;


                if (
                  attempt === 0
                ) {

                  await new Promise(
                    (resolve) =>
                      setTimeout(
                        resolve,
                        350
                      )
                  );
                }
              }
            }


            const stillLatest =
              sourcingVersionRef
                .current[
                  itemId
                ]
              === version;


            if (!stillLatest) {
              return;
            }


            if (saved) {

              setSourcingState(
                itemId,
                "saved",
              );

              return;
            }


            const message =
              finalError
                instanceof Error
                ? finalError.message
                : "Could not save sourcing.";


            setSourcingState(
              itemId,
              "error",
              message,
            );


            setError(
              `${snapshot.name}: ${message}`
            );
          }
        );


    sourcingChainsRef
      .current[
        itemId
      ] = next;


    return next;
  }


  function queueSourcingSave(
    item: WorkflowItem
  ) {

    const itemId =
      item.id;


    sourcingLatestRef
      .current[
        itemId
      ] = item;


    sourcingVersionRef
      .current[
        itemId
      ] = (
        sourcingVersionRef
          .current[
            itemId
          ]
        || 0
      ) + 1;


    setSourcingState(
      itemId,
      "saving",
    );


    const existing =
      sourcingTimersRef
        .current[
          itemId
        ];


    if (existing) {

      clearTimeout(
        existing
      );
    }


    sourcingTimersRef
      .current[
        itemId
      ] = setTimeout(
        () => {
          void enqueueSourcingSave(
            itemId
          );
        },
        500,
      );
  }


  function sourcingValue(
    item: WorkflowItem,
    key:
      | "supplier_id"
      | "availability_status"
      | "confirmed_quantity"
      | "confirmed_price"
      | "substitution_notes",
    value: string
  ) {

    if (!order) {
      return;
    }


    let nextValue:
      string
      | number
      | null =
        value;


    if (
      key ===
      "supplier_id"
    ) {

      nextValue =
        value
          ? Number(
              value
            )
          : null;
    }


    if (
      key ===
      "confirmed_quantity"
    ) {

      nextValue =
        value
          ? Number(
              value
            )
          : null;
    }


    if (
      key ===
      "confirmed_price"
    ) {

      nextValue =
        value === ""
          ? null
          : value;
    }


    const nextItem = {
      ...item,
      [key]:
        nextValue,
    } as WorkflowItem;


    setOrder(
      (current) => {

        if (!current) {
          return current;
        }


        return {
          ...current,

          status:
            "sourcing",

          quote_generated_at:
            null,

          customer_approved_at:
            null,

          goods_total:
            0,

          delivery_fee:
            0,

          service_fee:
            0,

          tax_total:
            0,

          final_total:
            0,

          items:
            current.items.map(
              (currentItem) =>
                currentItem.id
                === item.id
                ? nextItem
                : currentItem
            ),
        };
      }
    );


    queueSourcingSave(
      nextItem
    );
  }


  async function generateFinalPrice() {

    if (!order) {
      return;
    }


    try {

      setError("");

      setMessage(
        "Saving the latest sourcing and logistics..."
      );


      await waitForAutosaves(
        `order:${order.id}:`
      );


      const fresh =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}`
        );


      setOrder(
        fresh
      );


      const issues:
        string[] = [];


      for (
        const item
        of fresh.items
      ) {

        if (
          item.availability_status
          === "unverified"
        ) {

          issues.push(
            `${item.name}: availability not confirmed`
          );

          continue;
        }


        if (
          item.availability_status
          === "available"
          ||
          item.availability_status
          === "partial"
        ) {

          if (
            item.supplier_id
            == null
          ) {

            issues.push(
              `${item.name}: supplier missing`
            );
          }


          if (
            item.confirmed_quantity
            == null
            ||
            Number(
              item.confirmed_quantity
            ) <= 0
          ) {

            issues.push(
              `${item.name}: confirmed quantity missing`
            );
          }


          if (
            item.confirmed_price
            == null
            ||
            item.confirmed_price
            === ""
          ) {

            issues.push(
              `${item.name}: unit price missing`
            );
          }


          if (
            item.logistics_category_id
            == null
          ) {

            issues.push(
              `${item.name}: logistics category missing`
            );
          }


          if (
            item.total_weight_kg
            == null
          ) {

            issues.push(
              `${item.name}: cargo weight not saved`
            );
          }


          if (
            item.total_volume_l
            == null
          ) {

            issues.push(
              `${item.name}: cargo volume not saved`
            );
          }
        }
      }


      if (
        issues.length
      ) {

        setMessage("");

        setError(
          "Cannot generate final price yet. "
          + issues.join(
            " | "
          )
        );

        return;
      }


      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/quote`,
          {
            method:
              "POST",
          }
        );


      setOrder(
        updated
      );


      setMessage(
        "Final price generated. Call the customer for confirmation."
      );


    } catch (error) {

      setMessage("");

      setError(
        error instanceof Error
          ? error.message
          : "Could not generate final price."
      );
    }
  }


  async function recordCustomerResponse(
    decision:
      | "approved"
      | "wait"
      | "declined"
  ) {
    if (!order) {
      return;
    }

    if (
      decision === "declined"
      &&
      !window.confirm(
        "Customer declined this price. Cancel this order?"
      )
    ) {
      return;
    }

    try {
      setError("");
      setMessage("");


      setMessage(
        "Waiting for the latest automatic saves..."
      );


      await waitForAutosaves(
        `order:${order.id}:`
      );


      const fresh =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}`
        );


      setOrder(
        fresh
      );


      if (
        fresh.status
        !==
        "awaiting_buyer_approval"
        ||
        !fresh.quote_generated_at
      ) {

        throw new Error(
          "The final price became stale because order details changed. Generate the final price again."
        );
      }


      setMessage("");

      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/customer-response`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                decision,
              }),
          }
        );

      setOrder(
        updated
      );

      if (
        decision === "approved"
      ) {
        setMessage(
          "Customer approved. Awaiting payment confirmation."
        );
      }

      if (
        decision === "wait"
      ) {
        setMessage(
          "Customer asked to wait. Order remains pending."
        );
      }

      if (
        decision === "declined"
      ) {
        setMessage(
          "Customer declined. Order cancelled and kept in history."
        );
      }

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not record customer response."
      );
    }
  }


  async function confirmPayment() {
    if (!order) {
      return;
    }

    if (!paymentMethod.trim()) {
      setError(
        "Payment method is required."
      );

      return;
    }

    try {
      setError("");
      setMessage("");

      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/confirm-payment`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                amount:
                  Number(
                    order.final_total
                  ),

                method:
                  paymentMethod.trim(),

                reference:
                  paymentReference.trim()
                  || null,

                notes:
                  paymentNotes.trim()
                  || null,

                operator_id:
                  null,
              }),
          }
        );

      setOrder(
        updated
      );

      setMessage(
        "Payment confirmed. Supplier preparation can begin."
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not confirm payment."
      );
    }
  }


  async function beginPreparation() {
    if (!order) {
      return;
    }

    try {
      setError("");
      setMessage("");

      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/begin-preparation`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                operator_id:
                  null,

                notes:
                  "Preparation started from call-center workspace.",
              }),
          }
        );

      setOrder(
        updated
      );

      setMessage(
        "Supplier preparation started."
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not begin preparation."
      );
    }
  }


  async function markReadyForDispatch() {
    if (!order) {
      return;
    }

    try {
      setError("");
      setMessage("");

      const updated =
        await api<
          WorkflowOrder
        >(
          `/orders/${order.id}/ready-for-dispatch`,
          {
            method:
              "POST",

            body:
              JSON.stringify({
                operator_id:
                  null,

                notes:
                  "Marked ready from call-center workspace.",
              }),
          }
        );

      setOrder(
        updated
      );

      setMessage(
        "Order entered the StoreDash dispatch pool."
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not mark order ready for dispatch."
      );
    }
  }


  async function completeOrder() {
    if (!order) {
      return;
    }


    try {
      await api(
        `/orders/${order.id}/complete`,
        {
          method:
            "POST",
        }
      );


      router.push(
        "/dashboard"
      );


      router.refresh();


    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not complete order."
      );
    }
  }


  async function updateDelivery(
    action: string,
    notes?: string,
  ) {

    if (!order) {
      return;
    }

    try {

      setError("");
      setMessage("");

      await api(
        `/driver-operations/orders/${order.id}/status`,
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

      await loadOrder();

      if (
        action ===
        "deliver_and_complete"
      ) {
        setMessage(
          "Delivery completed."
        );
      }

      if (
        action ===
        "retry_delivery"
      ) {
        setMessage(
          "Delivery returned to active delivery."
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


  async function reportDeliveryProblem() {

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

    await updateDelivery(
      "problem",
      reason.trim(),
    );
  }


  if (loading) {
    return (
      <div className="card">
        Loading order workspace...
      </div>
    );
  }


  if (!order) {
    return (
      <div className="card">
        {error ||
          "Order not found."}
      </div>
    );
  }


  return (
    <>
      <div className="header">
        <div>
          <div className="eyebrow">
            Today's Order #
            {
              order.daily_number ??
              "—"
            }
          </div>

          <h1>
            {
              order.order_number
            }
          </h1>

          <p className="label">
            {customer
              ? `${customer.business_name} · ${customer.owner_name}`
              : "Customer"}
          </p>
        </div>


        <button
          className="btn btn-secondary"
          onClick={() =>
            router.push(
              "/dashboard"
            )
          }
        >
          Dashboard
        </button>
      </div>


      {error && (
        <div
          className="notice"
          style={{
            marginBottom:
              18,
          }}
        >
          {error}
        </div>
      )}


      {message && (
        <div
          className="notice"
          style={{
            marginBottom:
              18,
          }}
        >
          {message}
        </div>
      )}


      <div className="card">
        <div className="label">
          Workflow Status
        </div>

        <h2>
          {order.status
            .replaceAll(
              "_",
              " "
            )
            .toUpperCase()}
        </h2>

        {editable ? (
          <p className="label">
            This order is still a draft
            workflow and can be changed.
          </p>
        ) : (
          <p className="label">
            This order is finalized and
            locked.
          </p>
        )}
      </div>


      {editable && (
        <div
          className="card"
          style={{
            marginTop: 20,
          }}
        >
          <div className="header">
            <div>
              <h2>
                Requested Items
              </h2>

              <p className="label">
                Change the customer's
                request before finalizing.
              </p>
            </div>
          </div>


          {editableItems.map(
            (
              item,
              index
            ) => (
              <div
                key={
                  index
                }
                className="form-grid"
                style={{
                  marginBottom:
                    12,
                }}
              >
                <input
                  className="input"
                  value={
                    item.name
                  }
                  onChange={(
                    event
                  ) =>
                    updateEditableItem(
                      index,
                      "name",
                      event.target.value
                    )
                  }
                />

                <input
                  className="input"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={
                    item.requested_quantity
                  }
                  onChange={(
                    event
                  ) =>
                    updateEditableItem(
                      index,
                      "requested_quantity",
                      Number(
                        event.target.value
                      )
                    )
                  }
                />

                <input
                  className="input"
                  value={
                    item.unit
                  }
                  onChange={(
                    event
                  ) =>
                    updateEditableItem(
                      index,
                      "unit",
                      event.target.value
                    )
                  }
                />
              </div>
            )
          )}


          <button
            className="btn btn-secondary"
            onClick={() =>
              setEditableItems(
                [
                  ...editableItems,

                  {
                    name: "",
                    requested_quantity:
                      1,
                    unit:
                      "unit",
                  },
                ]
              )
            }
          >
            + Add Item
          </button>


          <textarea
            className="textarea"
            style={{
              marginTop: 15,
            }}
            value={
              notes
            }
            onChange={(
              event
            ) =>
              setNotes(
                event.target.value
              )
            }
            placeholder="Order notes"
          />


          <button
            className="btn"
            style={{
              marginTop: 15,
            }}
            onClick={
              saveDraft
            }
          >
            Save Requested Items
          </button>
        </div>
      )}


      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <div className="header">
          <div>
            <h2>
              Supplier Sourcing
            </h2>

            <p className="label">
              Confirm each requested
              product with a supplier.
            </p>
          </div>


          {customer && (
            <Link
              className="btn btn-secondary"
              href={
                `/customers/${customer.id}`
              }
            >
              Manage Usual Suppliers
            </Link>
          )}
        </div>


        {suppliers.length ===
          0 &&
          editable && (
          <div className="notice">
            This customer has no usual
            suppliers yet. Pair suppliers
            from the customer profile
            before sourcing.
          </div>
        )}


        {order.items.map(
          (item) => (
            <div
              key={
                item.id
              }
              style={{
                border:
                  "1px solid #e5e7eb",
                borderRadius:
                  12,
                padding:
                  16,
                marginTop:
                  14,
              }}
            >
              <div
                style={{
                  marginBottom:
                    12,
                }}
              >
                <strong>
                  {
                    item.name
                  }
                </strong>

                <div className="label">
                  Requested:{" "}
                  {
                    item.requested_quantity
                  }{" "}
                  {
                    item.unit
                  }
                </div>
              </div>


              <OrderItemLogistics
                orderId={order.id}
                itemId={item.id}
                productName={item.name}
                productSize={item.size}
                editable={editable}
                savedCategoryId={
                  item.logistics_category_id
                }
                savedTypeId={
                  item.logistics_type_id
                }
                savedSizeClass={
                  item.logistics_size_class
                }
                savedLoadUnitsEach={
                  item.load_units_each
                }
                savedTotalLoadUnits={
                  item.total_load_units
                }
                savedVariantKey={
                  item.logistics_variant_key
                }
                savedSizeDetail={
                  item.logistics_size_detail
                }
                savedMaterialClass={
                  item.physical_material_class
                }
                savedPhysicalConfidence={
                  item.physical_confidence
                }
                savedEstimationSource={
                  item.physical_estimation_source
                }
                savedWeightEach={
                  item.weight_kg_each
                }
                savedVolumeEach={
                  item.volume_l_each
                }
                savedHandlingEach={
                  item.handling_score_each
                }
                savedFragilityEach={
                  item.fragility_score_each
                }
              />


              {editable ? (
                <>
                  <div className="form-grid">
                    <label>
                      Supplier

                      <select
                        className="input"
                        value={
                          item.supplier_id ??
                          ""
                        }
                        onChange={(
                          event
                        ) =>
                          sourcingValue(
                            item,
                            "supplier_id",
                            event.target.value
                          )
                        }
                      >
                        <option value="">
                          Select supplier
                        </option>

                        {suppliers.map(
                          (
                            supplier
                          ) => (
                            <option
                              key={
                                supplier.supplier_id
                              }
                              value={
                                supplier.supplier_id
                              }
                            >
                              #
                              {
                                supplier.supplier_number
                              }{" "}
                              {
                                supplier.name
                              }
                            </option>
                          )
                        )}
                      </select>
                    </label>


                    <label>
                      Availability

                      <select
                        className="input"
                        value={
                          item.availability_status ||
                          "unverified"
                        }
                        onChange={(
                          event
                        ) =>
                          sourcingValue(
                            item,
                            "availability_status",
                            event.target.value
                          )
                        }
                      >
                        <option value="unverified">
                          Unverified
                        </option>

                        <option value="available">
                          Available
                        </option>

                        <option value="partial">
                          Partial
                        </option>

                        <option value="unavailable">
                          Unavailable
                        </option>
                      </select>
                    </label>


                    <label>
                      Confirmed Quantity

                      <input
                        className="input"
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          item.confirmed_quantity ??
                          ""
                        }
                        onChange={(
                          event
                        ) =>
                          sourcingValue(
                            item,
                            "confirmed_quantity",
                            event.target.value
                          )
                        }
                      />
                    </label>


                    <label>
                      Unit Price GH₵

                      <input
                        className="input"
                        type="number"
                        min="0"
                        step="0.01"
                        value={
                          item.confirmed_price ??
                          ""
                        }
                        onChange={(
                          event
                        ) =>
                          sourcingValue(
                            item,
                            "confirmed_price",
                            event.target.value
                          )
                        }
                      />
                    </label>
                  </div>


                  <textarea
                    className="textarea"
                    style={{
                      marginTop:
                        10,
                    }}
                    value={
                      item.substitution_notes ||
                      ""
                    }
                    onChange={(
                      event
                    ) =>
                      sourcingValue(
                        item,
                        "substitution_notes",
                        event.target.value
                      )
                    }
                    placeholder="Substitution, partial quantity, or sourcing notes"
                  />


                  <div
                    className="label"
                    style={{
                      marginTop:
                        10,
                    }}
                  >
                    {
                      sourcingSaveState[
                        item.id
                      ] === "saving"
                        ? "Saving sourcing..."

                        : sourcingSaveState[
                            item.id
                          ] === "saved"
                          ? "Saved ✓"

                          : sourcingSaveState[
                              item.id
                            ] === "error"
                            ? "Automatic save failed"

                            : "Sourcing saves automatically"
                    }
                  </div>
                </>
              ) : (
                <div className="details-list">
                  <div>
                    <span className="label">
                      Availability
                    </span>

                    <div>
                      {
                        item.availability_status
                      }
                    </div>
                  </div>

                  <div>
                    <span className="label">
                      Quantity
                    </span>

                    <div>
                      {
                        item.confirmed_quantity ??
                        "—"
                      }
                    </div>
                  </div>

                  <div>
                    <span className="label">
                      Unit price
                    </span>

                    <div>
                      GH₵
                      {
                        Number(
                          item.confirmed_price ||
                          0
                        ).toFixed(
                          2
                        )
                      }
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        )}
      </div>


      <OrderLoadSummary
        orderId={order.id}
      />


      {editable && (
        <div
          className="card"
          style={{
            marginTop: 20,
          }}
        >
          <h2>
            Final Price
          </h2>


          {!order.quote_generated_at ? (
            <div
              style={{
                marginTop:
                  16,
              }}
            >
              <p className="label">
                Generate StoreDash's customer price
                from the sourced goods, physical load,
                and delivery route.
              </p>

              <button
                className="btn"
                style={{
                  marginTop:
                    12,
                }}
                onClick={
                  generateFinalPrice
                }
              >
                Generate Final Price
              </button>
            </div>
          ) : (
            <>
              <div
                className="details-list"
                style={{
                  marginTop: 18,
                }}
              >
                <div>
                  <span className="label">
                    Goods
                  </span>

                  <div>
                    GH₵
                    {
                      Number(
                        order.goods_total
                      ).toFixed(2)
                    }
                  </div>
                </div>


                <div>
                  <span className="label">
                    Delivery
                  </span>

                  <div>
                    GH₵
                    {
                      Number(
                        order.delivery_fee
                      ).toFixed(2)
                    }
                  </div>
                </div>


                <div>
                  <span className="label">
                    Service Fee
                  </span>

                  <div>
                    GH₵
                    {
                      Number(
                        order.service_fee
                      ).toFixed(2)
                    }
                  </div>
                </div>


                <div>
                  <span className="label">
                    Tax
                  </span>

                  <div>
                    GH₵
                    {
                      Number(
                        order.tax_total ||
                        0
                      ).toFixed(2)
                    }
                  </div>
                </div>


                <div>
                  <span className="label">
                    Final Price
                  </span>

                  <div
                    style={{
                      fontSize: 26,
                      fontWeight: 800,
                    }}
                  >
                    GH₵
                    {
                      Number(
                        order.final_total
                      ).toFixed(2)
                    }
                  </div>
                </div>
              </div>


              <div
                style={{
                  marginTop: 22,
                  paddingTop: 18,
                  borderTop:
                    "1px solid #e5e7eb",
                }}
              >
                <h3>
                  Delivery Calculation
                </h3>

                <div className="details-list">
                  <div>
                    <span className="label">
                      Road distance
                    </span>

                    <div>
                      {
                        order.route_distance_km ??
                        "—"
                      }
                      {
                        order.route_distance_km !=
                        null
                          ? " km"
                          : ""
                      }
                    </div>
                  </div>


                  <div>
                    <span className="label">
                      Estimated travel
                    </span>

                    <div>
                      {
                        order.route_duration_minutes ??
                        "—"
                      }
                      {
                        order.route_duration_minutes !=
                        null
                          ? " min"
                          : ""
                      }
                    </div>
                  </div>


                  <div>
                    <span className="label">
                      Supplier stops
                    </span>

                    <div>
                      {
                        order.supplier_stop_count ??
                        "—"
                      }
                    </div>
                  </div>


                  <div>
                    <span className="label">
                      Total load
                    </span>

                    <div>
                      {
                        order.total_load_units ??
                        "—"
                      }
                      {
                        order.total_load_units !=
                        null
                          ? " units"
                          : ""
                      }
                    </div>
                  </div>
                </div>
              </div>


              <div
                style={{
                  marginTop: 22,
                  paddingTop: 18,
                  borderTop:
                    "1px solid #e5e7eb",
                }}
              >
                <h3>
                  Customer Response
                </h3>

                <p className="label">
                  Tell the customer the final price,
                  then record their decision.
                </p>


                <div
                  style={{
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                    marginTop: 14,
                  }}
                >
                  <button
                    className="btn"
                    onClick={() =>
                      recordCustomerResponse(
                        "approved"
                      )
                    }
                  >
                    Approved — Await Payment
                  </button>


                  <button
                    className="btn btn-secondary"
                    onClick={() =>
                      recordCustomerResponse(
                        "wait"
                      )
                    }
                  >
                    Customer Wants to Wait
                  </button>


                  <button
                    className="btn btn-secondary"
                    onClick={() =>
                      recordCustomerResponse(
                        "declined"
                      )
                    }
                  >
                    Customer Declined
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}


      {!editable && (
        <div
          className="card"
          style={{
            marginTop:
              20,
          }}
        >
          <h2>
            Final Price
          </h2>

          <div className="details-list">
            <div>
              <span className="label">
                Goods
              </span>

              <div>
                GH₵
                {
                  Number(
                    order.goods_total
                  ).toFixed(
                    2
                  )
                }
              </div>
            </div>

            <div>
              <span className="label">
                Delivery
              </span>

              <div>
                GH₵
                {
                  Number(
                    order.delivery_fee
                  ).toFixed(
                    2
                  )
                }
              </div>
            </div>

            <div>
              <span className="label">
                Service Fee
              </span>

              <div>
                GH₵
                {
                  Number(
                    order.service_fee
                  ).toFixed(
                    2
                  )
                }
              </div>
            </div>

            <div>
              <span className="label">
                Customer Total
              </span>

              <div>
                <strong>
                  GH₵
                  {
                    Number(
                      order.final_total
                    ).toFixed(
                      2
                    )
                  }
                </strong>
              </div>
            </div>
          </div>
        </div>
      )}


      {
        order.status ===
        "awaiting_payment"
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Payment Confirmation
            </h2>

            <p className="label">
              Customer approved GH₵
              {
                Number(
                  order.final_total
                ).toFixed(2)
              }.
              Confirm receipt before supplier
              preparation or rider commitment.
            </p>

            <div
              style={{
                display:
                  "grid",

                gap:
                  12,

                marginTop:
                  16,

                maxWidth:
                  520,
              }}
            >
              <input
                value={
                  paymentMethod
                }

                placeholder="Payment method — e.g. momo"

                onChange={
                  (event) =>
                    setPaymentMethod(
                      event.target.value
                    )
                }
              />

              <input
                value={
                  paymentReference
                }

                placeholder="Payment reference"

                onChange={
                  (event) =>
                    setPaymentReference(
                      event.target.value
                    )
                }
              />

              <textarea
                value={
                  paymentNotes
                }

                placeholder="Payment notes"

                onChange={
                  (event) =>
                    setPaymentNotes(
                      event.target.value
                    )
                }
              />

              <button
                className="btn"
                onClick={
                  confirmPayment
                }
              >
                Confirm Payment
              </button>
            </div>
          </div>
        )
      }


      {
        order.status ===
        "payment_confirmed"
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Payment Confirmed
            </h2>

            <p className="label">
              The customer has paid.
              StoreDash can now authorize
              supplier preparation.
            </p>

            <button
              className="btn"
              style={{
                marginTop:
                  12,
              }}
              onClick={
                beginPreparation
              }
            >
              Begin Preparation
            </button>
          </div>
        )
      }


      {
        order.status ===
        "preparing"
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Supplier Preparing
            </h2>

            <p className="label">
              Only mark this ready when the
              sourced goods are physically ready
              for StoreDash pickup.
            </p>

            <button
              className="btn"
              style={{
                marginTop:
                  12,
              }}
              onClick={
                markReadyForDispatch
              }
            >
              Mark Ready for Dispatch
            </button>
          </div>
        )
      }


      {
        order.status ===
        "ready_for_dispatch"
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Ready for Dispatch
            </h2>

            <p className="label">
              This paid order is now eligible
              for StoreDash batch routing.
            </p>

            <button
              className="btn"
              style={{
                marginTop:
                  12,
              }}
              onClick={() =>
                router.push(
                  `/dispatch?orderId=${order.id}`
                )
              }
            >
              Dispatch This Order
            </button>
          </div>
        )
      }





      {
        (
          order.status ===
            "driver_assigned"
          ||
          order.status ===
            "pickup_in_progress"
          ||
          order.status ===
            "out_for_delivery"
        )
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Delivery Control
            </h2>

            <p className="label">
              This order is locked while
              delivery is active.
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
              {
                order.status ===
                  "driver_assigned"
                && (
                  <button
                    className="btn"
                    onClick={() =>
                      updateDelivery(
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
                  order.status ===
                    "driver_assigned"
                  ||
                  order.status ===
                    "pickup_in_progress"
                )
                && (
                  <button
                    className="btn"
                    onClick={() =>
                      updateDelivery(
                        "out_for_delivery"
                      )
                    }
                  >
                    Out for Delivery
                  </button>
                )
              }

              {
                order.status ===
                  "out_for_delivery"
                && (
                  <>
                    <button
                      className="btn"
                      onClick={() =>
                        updateDelivery(
                          "deliver_and_complete"
                        )
                      }
                    >
                      Delivered — Finish Order
                    </button>

                    <button
                      className="btn btn-secondary"
                      onClick={
                        reportDeliveryProblem
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
      }


      {
        order.status ===
        "failed"
        && (
          <div
            className="card"
            style={{
              marginTop:
                20,
            }}
          >
            <h2>
              Delivery Needs Resolution
            </h2>

            <p className="label">
              This order remains locked until
              the delivery problem is resolved.
            </p>

            <button
              className="btn"
              style={{
                marginTop:
                  12,
              }}
              onClick={() =>
                updateDelivery(
                  "retry_delivery"
                )
              }
            >
              Retry Delivery
            </button>
          </div>
        )
      }


      {order.status ===
        "completed" && (
        <div
          className="card"
          style={{
            marginTop:
              20,
          }}
        >
          <strong>
            Order completed.
          </strong>
        </div>
      )}
    </>
  );
}
