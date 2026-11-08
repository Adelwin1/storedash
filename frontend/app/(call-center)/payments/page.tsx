"use client";

import Link from "next/link";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  AlertTriangle,
  CheckCircle2,
  CircleDollarSign,
  CreditCard,
  RefreshCw,
  ShieldCheck,
  Truck,
} from "lucide-react";

import { api } from "@/lib/api";


type PaymentSummary = {
  incoming_pending: number;
  incoming_succeeded: number;
  payout_attention: number;
  exceptions: number;
};


type IncomingPayment = {
  id: number;
  order_id: number;
  order_number: string | null;
  amount: string;
  currency: string;
  payer_phone: string | null;
  payment_method: string | null;
  status: string;
  provider_status: string | null;
  client_reference: string;
  failure_reason: string | null;
  created_at: string | null;
  confirmed_at: string | null;
};


type OutgoingPayout = {
  id: number;
  recipient_type: string;
  supplier_id: number | null;
  driver_id: number | null;
  order_id: number | null;
  delivery_batch_id: number | null;
  amount: string;
  currency: string;
  reason: string;
  status: string;
  recipient_name: string | null;
  recipient_phone: string | null;
  can_control: boolean;
  failure_reason: string | null;
  created_at: string | null;
  completed_at: string | null;
};


type PaymentDashboard = {
  role: string;
  can_control_money: boolean;
  summary: PaymentSummary;
  incoming: IncomingPayment[];
  outgoing: OutgoingPayout[];
};


type PayoutRecipientOption = {
  id: number;
  name: string;
  phone: string;
  payment_phone?: string | null;
  payment_name?: string | null;
};


type PayoutProfileItem = {
  id: number;
  recipient_type: string;
  supplier_id: number | null;
  driver_id: number | null;
  payment_name: string;
  payment_phone: string;
  network: string | null;
  is_verified: boolean;
  is_locked: boolean;
  is_active: boolean;
  version: number;
};


type PayoutSetup = {
  suppliers: PayoutRecipientOption[];
  drivers: PayoutRecipientOption[];
  profiles: PayoutProfileItem[];
};


type VerificationEvent = {
  id: number;
  event_type: string;
  sender: string | null;
  body: string | null;
  received_at: string | null;
  device_id: string | null;
  direction: string | null;
  amount: string | null;
  phone: string | null;
  transaction_reference: string | null;
  payer_name: string | null;
  suggested_order_id: number | null;
  expected_payer_name: string | null;
  reason: string | null;
  can_resolve: boolean;
  can_defer: boolean;
};


type VerificationQueue = {
  count: number;
  events: VerificationEvent[];
};


export default function PaymentsPage() {
  const [
    data,
    setData,
  ] = useState<PaymentDashboard | null>(
    null
  );

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    recordingPayoutId,
    setRecordingPayoutId,
  ] = useState<number | null>(
    null
  );


  const [
    payoutSetup,
    setPayoutSetup,
  ] = useState<PayoutSetup | null>(
    null
  );

  const [
    recipientType,
    setRecipientType,
  ] = useState("supplier");

  const [
    recipientId,
    setRecipientId,
  ] = useState("");

  const [
    payoutName,
    setPayoutName,
  ] = useState("");

  const [
    payoutPhone,
    setPayoutPhone,
  ] = useState("");

  const [
    payoutNetwork,
    setPayoutNetwork,
  ] = useState("mtn");

  const [
    savingProfile,
    setSavingProfile,
  ] = useState(false);

  const [
    setupMessage,
    setSetupMessage,
  ] = useState("");


  const [
    verificationQueue,
    setVerificationQueue,
  ] = useState<VerificationQueue | null>(
    null
  );

  const [
    resolvingEventId,
    setResolvingEventId,
  ] = useState<number | null>(
    null
  );




  const loadDashboard =
    useCallback(
      async (
        quiet = false
      ) => {
        try {
          if (quiet) {
            setRefreshing(true);
          } else {
            setLoading(true);
          }

          setError("");

          const result =
            await api<PaymentDashboard>(
              "/payments/dashboard"
            );

          setData(result);

        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load payments."
          );

        } finally {
          setLoading(false);
          setRefreshing(false);
        }
      },
      []
    );


  async function loadVerificationQueue() {
    try {
      const result =
        await api<VerificationQueue>(
          "/payments/sms-relay/verification"
        );

      setVerificationQueue(
        result
      );

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load payment verification queue."
      );
    }
  }


  async function approveVerificationEvent(
    event: VerificationEvent
  ) {
    if (
      !event.can_resolve
      || !event.suggested_order_id
    ) {
      return;
    }

    if (
      !window.confirm(
        `Approve StoreDash match to order #${event.suggested_order_id}?`
      )
    ) {
      return;
    }

    try {
      setResolvingEventId(event.id);
      setError("");

      await api(
        `/payments/sms-relay/events/${event.id}/resolve-incoming`,
        {
          method: "POST",
          body: JSON.stringify({
            order_id:
              event.suggested_order_id,
          }),
        }
      );

      await loadVerificationQueue();
      await loadDashboard(true);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not approve payment match."
      );

    } finally {
      setResolvingEventId(null);
    }
  }


  async function deferVerificationEvent(
    event: VerificationEvent
  ) {
    if (!event.can_defer) {
      return;
    }

    try {
      setResolvingEventId(event.id);
      setError("");

      await api(
        `/payments/sms-relay/events/${event.id}/not-sure`,
        {
          method: "POST",
        }
      );

      await loadVerificationQueue();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not send payment to manager review."
      );

    } finally {
      setResolvingEventId(null);
    }
  }


  async function loadPayoutSetup() {
    try {
      const result =
        await api<PayoutSetup>(
          "/payments/payout-setup"
        );

      setPayoutSetup(result);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load payout setup."
      );
    }
  }


  function selectRecipient(
    value: string
  ) {
    setRecipientId(value);

    if (!value || !payoutSetup) {
      return;
    }

    const source =
      recipientType === "supplier"
        ? payoutSetup.suppliers
        : payoutSetup.drivers;

    const selected =
      source.find(
        item =>
          item.id === Number(value)
      );

    if (!selected) {
      return;
    }

    setPayoutName(
      selected.payment_name
      ?? selected.name
    );

    setPayoutPhone(
      selected.payment_phone
      ?? selected.phone
    );
  }


  async function createAndLockPayoutProfile() {
    if (
      !recipientId
      || !payoutName.trim()
      || !payoutPhone.trim()
    ) {
      setError(
        "Recipient, payment name, and payment phone are required."
      );

      return;
    }

    try {
      setSavingProfile(true);
      setError("");
      setSetupMessage("");

      const created =
        await api<{
          payout_profile_id: number;
        }>(
          "/payments/payout-profiles",
          {
            method: "POST",

            body: JSON.stringify({
              recipient_type:
                recipientType,

              supplier_id:
                recipientType === "supplier"
                  ? Number(recipientId)
                  : null,

              driver_id:
                recipientType === "driver"
                  ? Number(recipientId)
                  : null,

              payment_phone:
                payoutPhone.trim(),

              payment_name:
                payoutName.trim(),

              network:
                payoutNetwork,

              notes:
                "Temporary launch payout profile created by StoreDash admin.",
            }),
          }
        );

      await api(
        `/payments/payout-profiles/${created.payout_profile_id}/manual-verify-and-lock`,
        {
          method: "POST",
        }
      );

      setSetupMessage(
        "Payout destination created, verified, and locked."
      );

      setRecipientId("");
      setPayoutName("");
      setPayoutPhone("");

      await loadPayoutSetup();
      await loadDashboard(true);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create payout profile."
      );

    } finally {
      setSavingProfile(false);
    }
  }


  async function recordExternalPayout(
    payout: OutgoingPayout
  ) {
    if (
      !data?.can_control_money
    ) {
      return;
    }

    const reference =
      window.prompt(
        `Enter the MoMo/bank transaction reference for GH₵${Number(
          payout.amount
        ).toFixed(2)} paid to ${
          payout.recipient_name
          ?? payout.recipient_phone
          ?? "this recipient"
        }:`
      );

    if (
      !reference
      || !reference.trim()
    ) {
      return;
    }

    if (
      !window.confirm(
        `Confirm that GH₵${Number(
          payout.amount
        ).toFixed(2)} was actually sent to ${
          payout.recipient_name
          ?? payout.recipient_phone
          ?? "this recipient"
        }?`
      )
    ) {
      return;
    }

    try {
      setRecordingPayoutId(
        payout.id
      );

      setError("");

      await api(
        `/payments/payouts/${payout.id}/record-external`,
        {
          method: "POST",

          body: JSON.stringify({
            transaction_reference:
              reference.trim(),
          }),
        }
      );

      await loadDashboard(
        true
      );

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not record payout."
      );

    } finally {
      setRecordingPayoutId(
        null
      );
    }
  }


  useEffect(() => {
    void loadDashboard();

    const timer =
      window.setInterval(
        () => {
          void loadDashboard(true);
        },
        5000
      );

    return () => {
      window.clearInterval(timer);
    };
  }, [loadDashboard]);


  useEffect(() => {
    if (
      data?.role === "admin"
    ) {
      void loadPayoutSetup();
    }
  }, [data?.role]);


  useEffect(() => {
    if (!data) {
      return;
    }

    void loadVerificationQueue();

    const timer =
      window.setInterval(
        () => {
          void loadVerificationQueue();
        },
        5000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };
  }, [data?.role]);


  if (
    loading
    && !data
  ) {
    return (
      <div style={{ padding: 28 }}>
        Loading payments...
      </div>
    );
  }


  return (
    <div
      style={{
        padding: 28,
        display: "grid",
        gap: 22,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 18,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: 30,
            }}
          >
            Payments
          </h1>

          <p
            style={{
              marginTop: 8,
              opacity: 0.7,
            }}
          >
            Incoming customer payments,
            supplier payouts, driver payouts,
            and financial exceptions.
          </p>
        </div>

        <button
          type="button"
          className="btn"
          onClick={() =>
            void loadDashboard(true)
          }
          disabled={refreshing}
        >
          <RefreshCw
            size={17}
          />

          {refreshing
            ? "Refreshing..."
            : "Refresh"}
        </button>
      </div>


      {error && (
        <div
          className="card"
          style={{
            borderColor:
              "rgba(180,40,40,.25)",
          }}
        >
          <strong>
            Payment dashboard error
          </strong>

          <div
            style={{
              marginTop: 6,
            }}
          >
            {error}
          </div>
        </div>
      )}


      {data && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(210px, 1fr))",
              gap: 16,
            }}
          >
            <SummaryCard
              icon={
                <CreditCard size={21} />
              }
              title="Awaiting payment"
              value={
                data.summary
                  .incoming_pending
              }
              subtitle="Customer payments pending"
            />

            <SummaryCard
              icon={
                <CheckCircle2 size={21} />
              }
              title="Confirmed"
              value={
                data.summary
                  .incoming_succeeded
              }
              subtitle="Customer payments confirmed"
            />

            <SummaryCard
              icon={
                <CircleDollarSign
                  size={21}
                />
              }
              title="Payout attention"
              value={
                data.summary
                  .payout_attention
              }
              subtitle={
                data.can_control_money
                  ? "Requires financial action"
                  : "Manager-controlled"
              }
            />

            <SummaryCard
              icon={
                <AlertTriangle
                  size={21}
                />
              }
              title="Exceptions"
              value={
                data.summary.exceptions
              }
              subtitle="Failed or unresolved money events"
            />
          </div>


          <section className="card">
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
              }}
            >
              <ShieldCheck size={20} />

              <strong>
                {data.role === "admin"
                  ? "Administrator finance view"
                  : data.role === "manager"
                    ? "Manager finance view"
                    : "Operator payment view"}
              </strong>
            </div>

            <p
              className="label"
              style={{
                marginBottom: 0,
                marginTop: 8,
              }}
            >
              {data.can_control_money
                ? (
                  "You can manage outgoing financial actions. "
                  + "StoreDash still controls payout amounts "
                  + "and verified destinations."
                )
                : (
                  "You can monitor payment and payout status. "
                  + "Outgoing money remains controlled by "
                  + "the manager or administrator."
                )}
            </p>
          </section>


          <section className="card">
            <h2>
              Incoming Customer Payments
            </h2>

            {data.incoming.length === 0
              ? (
                <p className="label">
                  No customer payment transactions yet.
                </p>
              )
              : (
                <div
                  style={{
                    overflowX: "auto",
                  }}
                >
                  <table
                    style={{
                      width: "100%",
                      borderCollapse:
                        "collapse",
                    }}
                  >
                    <thead>
                      <tr>
                        <TableHead>
                          Order
                        </TableHead>

                        <TableHead>
                          Amount
                        </TableHead>

                        <TableHead>
                          Payer
                        </TableHead>

                        <TableHead>
                          Method
                        </TableHead>

                        <TableHead>
                          Status
                        </TableHead>

                        <TableHead>
                          Reference
                        </TableHead>
                      </tr>
                    </thead>

                    <tbody>
                      {data.incoming.map(
                        payment => (
                          <tr
                            key={
                              payment.id
                            }
                          >
                            <TableCell>
                              <Link
                                href={
                                  `/orders/${payment.order_id}`
                                }
                              >
                                {
                                  payment.order_number
                                  ?? `Order #${payment.order_id}`
                                }
                              </Link>
                            </TableCell>

                            <TableCell>
                              GH₵
                              {Number(
                                payment.amount
                              ).toFixed(2)}
                            </TableCell>

                            <TableCell>
                              {
                                payment.payer_phone
                                ?? "—"
                              }
                            </TableCell>

                            <TableCell>
                              {
                                payment.payment_method
                                ?? "—"
                              }
                            </TableCell>

                            <TableCell>
                              <StatusBadge
                                status={
                                  payment.status
                                }
                              />
                            </TableCell>

                            <TableCell>
                              {
                                payment.client_reference
                              }
                            </TableCell>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              )}
          </section>


          <section className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
                alignItems: "center",
              }}
            >
              <h2>
                Supplier & Driver Payouts
              </h2>

              {!data.can_control_money && (
                <span className="label">
                  View only
                </span>
              )}
            </div>

            {data.outgoing.length === 0
              ? (
                <p className="label">
                  No supplier or driver payouts yet.
                </p>
              )
              : (
                <div
                  style={{
                    overflowX: "auto",
                  }}
                >
                  <table
                    style={{
                      width: "100%",
                      borderCollapse:
                        "collapse",
                    }}
                  >
                    <thead>
                      <tr>
                        <TableHead>
                          Type
                        </TableHead>

                        <TableHead>
                          Recipient
                        </TableHead>

                        <TableHead>
                          Destination
                        </TableHead>

                        <TableHead>
                          Amount
                        </TableHead>

                        <TableHead>
                          Reason
                        </TableHead>

                        <TableHead>
                          Status
                        </TableHead>

                        <TableHead>
                          Action
                        </TableHead>
                      </tr>
                    </thead>

                    <tbody>
                      {data.outgoing.map(
                        payout => (
                          <tr
                            key={
                              payout.id
                            }
                          >
                            <TableCell>
                              {pretty(
                                payout.recipient_type
                              )}
                            </TableCell>

                            <TableCell>
                              {
                                payout.recipient_name
                                ?? (
                                  payout.supplier_id
                                    ? `Supplier #${payout.supplier_id}`
                                    : payout.driver_id
                                      ? `Driver #${payout.driver_id}`
                                      : "—"
                                )
                              }
                            </TableCell>

                            <TableCell>
                              {
                                payout.recipient_phone
                                ?? "—"
                              }
                            </TableCell>

                            <TableCell>
                              GH₵
                              {Number(
                                payout.amount
                              ).toFixed(2)}
                            </TableCell>

                            <TableCell>
                              {pretty(
                                payout.reason
                              )}
                            </TableCell>

                            <TableCell>
                              <StatusBadge
                                status={
                                  payout.status
                                }
                              />
                            </TableCell>

                            <TableCell>
                              {
                                payout.can_control
                                && payout.status
                                  !== "succeeded"
                                && payout.status
                                  !== "cancelled"
                                  ? (
                                    <button
                                      type="button"
                                      className="btn"
                                      disabled={
                                        recordingPayoutId
                                        === payout.id
                                      }
                                      onClick={() =>
                                        void recordExternalPayout(
                                          payout
                                        )
                                      }
                                    >
                                      {
                                        recordingPayoutId
                                        === payout.id
                                          ? "Recording..."
                                          : "Record Paid"
                                      }
                                    </button>
                                  )
                                  : (
                                    <span className="label">
                                      {
                                        payout.status
                                        === "succeeded"
                                          ? "Paid"
                                          : "View only"
                                      }
                                    </span>
                                  )
                              }
                            </TableCell>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              )}
          </section>


          <section className="card">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div>
                <h2
                  style={{
                    marginBottom: 4,
                  }}
                >
                  Needs Verification
                </h2>

                <p
                  className="label"
                  style={{
                    margin: 0,
                  }}
                >
                  Payments StoreDash could not
                  safely match automatically.
                </p>
              </div>

              <strong>
                {
                  verificationQueue?.count
                  ?? 0
                }
              </strong>
            </div>

            {
              !verificationQueue
              || verificationQueue.events.length
              === 0
                ? (
                  <p className="label">
                    No unresolved payment events.
                  </p>
                )
                : (
                  <div
                    style={{
                      overflowX: "auto",
                      marginTop: 16,
                    }}
                  >
                    <table
                      style={{
                        width: "100%",
                        borderCollapse:
                          "collapse",
                      }}
                    >
                      <thead>
                        <tr>
                          <TableHead>
                            Amount
                          </TableHead>

                          <TableHead>
                            Phone
                          </TableHead>

                          <TableHead>
                            Reference
                          </TableHead>

                          <TableHead>
                            Reason
                          </TableHead>

                          <TableHead>
                            SMS
                          </TableHead>

                          <TableHead>
                            Action
                          </TableHead>
                        </tr>
                      </thead>

                      <tbody>
                        {
                          verificationQueue
                          .events
                          .map(
                            event => (
                              <tr
                                key={
                                  event.id
                                }
                              >
                                <TableCell>
                                  {
                                    event.amount
                                      ? (
                                        `GH₵${Number(
                                          event.amount
                                        ).toFixed(2)}`
                                      )
                                      : "—"
                                  }
                                </TableCell>

                                <TableCell>
                                  {
                                    event.phone
                                    ?? "—"
                                  }
                                </TableCell>

                                <TableCell>
                                  {
                                    event.transaction_reference
                                    ?? "—"
                                  }
                                </TableCell>

                                <TableCell>
                                  {
                                    event.reason
                                    ?? "—"
                                  }
                                </TableCell>

                                <TableCell>
                                  <span
                                    title={
                                      event.body
                                      ?? ""
                                    }
                                  >
                                    {
                                      event.body
                                        ? (
                                          event.body.length
                                          > 60
                                            ? (
                                              event.body.slice(
                                                0,
                                                60
                                              )
                                              + "…"
                                            )
                                            : event.body
                                        )
                                        : "—"
                                    }
                                  </span>
                                </TableCell>

                                <TableCell>
                                  {
                                    event.can_resolve
                                    && event.suggested_order_id
                                      ? (
                                        <div
                                          style={{
                                            display: "flex",
                                            gap: 8,
                                            flexWrap: "wrap",
                                          }}
                                        >
                                          <button
                                            type="button"
                                            className="btn"
                                            disabled={
                                              resolvingEventId
                                              === event.id
                                            }
                                            onClick={
                                              () =>
 void approveVerificationEvent(
   event
 )
                                            }
                                          >
                                            Approve
                                          </button>

                                          {
                                            event.can_defer
                                              ? (
                                                <button
                                                  type="button"
                                                  className="btn"
                                                  disabled={
                                                    resolvingEventId
                                                    === event.id
                                                  }
                                                  onClick={
                                                    () =>
 void deferVerificationEvent(
   event
 )
                                                  }
                                                >
                                                  Not sure
                                                </button>
                                              )
                                              : null
                                          }
                                        </div>
                                      )
                                      : (
                                        <span className="label">
                                          Manager review
                                        </span>
                                      )
                                  }
                                </TableCell>
                              </tr>
                            )
                          )
                        }
                      </tbody>
                    </table>
                  </div>
                )
            }
          </section>


          {
            data.role === "admin"
            && payoutSetup
            && (
              <section className="card">
                <h2>
                  Payout Setup
                </h2>

                <p className="label">
                  Create and lock the MoMo destination
                  StoreDash will use for a supplier or driver.
                  Managers can pay these destinations but
                  cannot change them.
                </p>

                {setupMessage && (
                  <div
                    style={{
                      marginTop: 12,
                      marginBottom: 12,
                      fontWeight: 700,
                    }}
                  >
                    {setupMessage}
                  </div>
                )}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(190px, 1fr))",
                    gap: 12,
                    marginTop: 16,
                  }}
                >
                  <select
                    value={recipientType}
                    onChange={
                      event => {
                        setRecipientType(
                          event.target.value
                        );

                        setRecipientId("");
                        setPayoutName("");
                        setPayoutPhone("");
                      }
                    }
                  >
                    <option value="supplier">
                      Supplier
                    </option>

                    <option value="driver">
                      Driver
                    </option>
                  </select>

                  <select
                    value={recipientId}
                    onChange={
                      event =>
                        selectRecipient(
                          event.target.value
                        )
                    }
                  >
                    <option value="">
                      Select recipient
                    </option>

                    {
                      (
                        recipientType === "supplier"
                          ? payoutSetup.suppliers
                          : payoutSetup.drivers
                      ).map(
                        item => (
                          <option
                            key={item.id}
                            value={item.id}
                          >
                            {item.name}
                          </option>
                        )
                      )
                    }
                  </select>

                  <input
                    value={payoutName}
                    placeholder="Registered MoMo name"
                    onChange={
                      event =>
                        setPayoutName(
                          event.target.value
                        )
                    }
                  />

                  <input
                    value={payoutPhone}
                    placeholder="MoMo phone"
                    onChange={
                      event =>
                        setPayoutPhone(
                          event.target.value
                        )
                    }
                  />

                  <select
                    value={payoutNetwork}
                    onChange={
                      event =>
                        setPayoutNetwork(
                          event.target.value
                        )
                    }
                  >
                    <option value="mtn">
                      MTN MoMo
                    </option>

                    <option value="telecel">
                      Telecel Cash
                    </option>

                    <option value="airteltigo">
                      AT Money
                    </option>
                  </select>

                  <button
                    type="button"
                    className="btn"
                    disabled={savingProfile}
                    onClick={() =>
                      void createAndLockPayoutProfile()
                    }
                  >
                    {
                      savingProfile
                        ? "Saving..."
                        : "Create & Lock"
                    }
                  </button>
                </div>


                <div
                  style={{
                    overflowX: "auto",
                    marginTop: 24,
                  }}
                >
                  <table
                    style={{
                      width: "100%",
                      borderCollapse:
                        "collapse",
                    }}
                  >
                    <thead>
                      <tr>
                        <TableHead>
                          Type
                        </TableHead>

                        <TableHead>
                          Name
                        </TableHead>

                        <TableHead>
                          Phone
                        </TableHead>

                        <TableHead>
                          Network
                        </TableHead>

                        <TableHead>
                          Verified
                        </TableHead>

                        <TableHead>
                          Locked
                        </TableHead>
                      </tr>
                    </thead>

                    <tbody>
                      {
                        payoutSetup.profiles.map(
                          profile => (
                            <tr key={profile.id}>
                              <TableCell>
                                {pretty(
                                  profile.recipient_type
                                )}
                              </TableCell>

                              <TableCell>
                                {profile.payment_name}
                              </TableCell>

                              <TableCell>
                                {profile.payment_phone}
                              </TableCell>

                              <TableCell>
                                {profile.network ?? "—"}
                              </TableCell>

                              <TableCell>
                                {
                                  profile.is_verified
                                    ? "Yes"
                                    : "No"
                                }
                              </TableCell>

                              <TableCell>
                                {
                                  profile.is_locked
                                    ? "Yes"
                                    : "No"
                                }
                              </TableCell>
                            </tr>
                          )
                        )
                      }
                    </tbody>
                  </table>
                </div>
              </section>
            )
          }


          <div
            className="card"
            style={{
              display: "flex",
              gap: 10,
              alignItems: "center",
            }}
          >
            <Truck size={19} />

            <div>
              <strong>
                Payment relay
              </strong>

              <div
                className="label"
                style={{
                  marginTop: 3,
                }}
              >
                StoreDash SMS relay not connected yet.
                This page automatically refreshes every
                5 seconds until real-time payment events
                are connected.
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}


function SummaryCard({
  icon,
  title,
  value,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  value: number;
  subtitle: string;
}) {
  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
        }}
      >
        {icon}

        <strong>
          {title}
        </strong>
      </div>

      <div
        style={{
          fontSize: 30,
          fontWeight: 700,
          marginTop: 12,
        }}
      >
        {value}
      </div>

      <div
        className="label"
        style={{
          marginTop: 5,
        }}
      >
        {subtitle}
      </div>
    </div>
  );
}


function StatusBadge({
  status,
}: {
  status: string;
}) {
  return (
    <span
      style={{
        display: "inline-block",
        borderRadius: 999,
        padding: "5px 9px",
        background:
          "rgba(0,0,0,.06)",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {pretty(status)}
    </span>
  );
}


function TableHead({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <th
      style={{
        textAlign: "left",
        padding: "11px 10px",
        borderBottom:
          "1px solid rgba(0,0,0,.10)",
        fontSize: 12,
        opacity: 0.65,
      }}
    >
      {children}
    </th>
  );
}


function TableCell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <td
      style={{
        padding: "12px 10px",
        borderBottom:
          "1px solid rgba(0,0,0,.06)",
        fontSize: 14,
      }}
    >
      {children}
    </td>
  );
}


function pretty(
  value: string
) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, char =>
      char.toUpperCase()
    );
}
