"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  api,
} from "@/lib/api";


type OutgoingPayout = {
  id: number;
  recipient_type: string;
  order_id: number | null;
  status: string;
};


type PaymentDashboard = {
  role: string;

  summary: {
    incoming_succeeded: number;
  };

  outgoing: OutgoingPayout[];
};


type ActionAlert = {
  title: string;
  message: string;
};


export default function StoreDashActionAlerts() {
  const [
    actionAlert,
    setActionAlert,
  ] = useState<ActionAlert | null>(
    null
  );


  const checkActions =
    useCallback(
      async () => {
        try {
          const data =
            await api<PaymentDashboard>(
              "/payments/dashboard"
            );

          const actionKeys: string[] = [];


          // ---------------------------------------------
          // CUSTOMER PAYMENT -> OPERATIONS CALL SUPPLIERS
          // ---------------------------------------------
          if (
            data.role === "operations"
            && data.summary.incoming_succeeded > 0
          ) {
            actionKeys.push(
              `customer-payment:${data.summary.incoming_succeeded}`
            );
          }


          // ---------------------------------------------
          // SUPPLIERS PAID -> OPERATIONS CONFIRM + DISPATCH
          // ---------------------------------------------
          if (data.role === "operations") {
            const supplierGroups =
              new Map<
                number,
                OutgoingPayout[]
              >();

            for (
              const payout
              of data.outgoing
            ) {
              if (
                payout.recipient_type
                  !== "supplier"
                || !payout.order_id
              ) {
                continue;
              }

              const group =
                supplierGroups.get(
                  payout.order_id
                )
                ?? [];

              group.push(
                payout
              );

              supplierGroups.set(
                payout.order_id,
                group
              );
            }

            for (
              const [
                orderId,
                payouts,
              ]
              of supplierGroups
            ) {
              if (
                payouts.length > 0
                && payouts.every(
                  payout =>
                    payout.status
                      === "succeeded"
                )
              ) {
                actionKeys.push(
                  `dispatch:${orderId}`
                );
              }
            }
          }


          // ---------------------------------------------
          // DELIVERY COMPLETE -> MANAGER PAYS DRIVER
          // ---------------------------------------------
          if (
            data.role === "manager"
            || data.role === "admin"
          ) {
            for (
              const payout
              of data.outgoing
            ) {
              if (
                payout.recipient_type
                  === "driver"
                && (
                  payout.status
                    === "pending_approval"
                  || payout.status
                    === "approved"
                  || payout.status
                    === "processing"
                )
              ) {
                actionKeys.push(
                  `driver:${payout.id}`
                );
              }
            }
          }


          actionKeys.sort();

          const snapshot =
            actionKeys.join("|");

          const storageKey =
            `storedash-global-actions:${data.role}`;

          const previous =
            window.sessionStorage.getItem(
              storageKey
            );


          // First load establishes baseline.
          // Do not alert for old existing actions.
          if (previous === null) {
            window.sessionStorage.setItem(
              storageKey,
              snapshot
            );

            return;
          }


          const previousKeys =
            new Set(
              previous
                .split("|")
                .filter(Boolean)
            );

          const fresh =
            actionKeys.filter(
              item =>
                !previousKeys.has(
                  item
                )
            );

          window.sessionStorage.setItem(
            storageKey,
            snapshot
          );


          if (
            fresh.length === 0
          ) {
            return;
          }


          let alert:
            ActionAlert;


          if (
            fresh.some(
              item =>
                item.startsWith(
                  "driver:"
                )
            )
          ) {
            alert = {
              title:
                "DRIVER PAYMENT READY",

              message:
                "Delivery completed. Send the exact driver payout shown in Payments.",
            };

          } else if (
            fresh.some(
              item =>
                item.startsWith(
                  "dispatch:"
                )
            )
          ) {
            alert = {
              title:
                "SUPPLIER PAYMENT CONFIRMED",

              message:
                "StoreDash payment to the supplier was confirmed. Call the supplier to confirm receipt, then proceed with dispatch.",
            };

          } else {
            alert = {
              title:
                "CUSTOMER PAYMENT RECEIVED",

              message:
                "Customer payment was confirmed. Call the suppliers now and begin order preparation.",
            };
          }


          setActionAlert(
            alert
          );


          // ---------------------------------------------
          // BROWSER TAB ATTENTION
          // ---------------------------------------------
          const previousTitle =
            document.title;

          document.title =
            "● StoreDash action needed";

          window.setTimeout(
            () => {
              document.title =
                previousTitle;
            },
            6000
          );


          // ---------------------------------------------
          // SHORT BEEP
          // ---------------------------------------------
          try {
            const context =
              new window.AudioContext();

            const oscillator =
              context.createOscillator();

            const gain =
              context.createGain();

            oscillator.connect(
              gain
            );

            gain.connect(
              context.destination
            );

            gain.gain.value =
              0.08;

            oscillator.frequency.value =
              880;

            oscillator.start();

            oscillator.stop(
              context.currentTime
                + 0.18
            );

            window.setTimeout(
              () => {
                void context.close();
              },
              300
            );

          } catch {
            // Some browsers block sound
            // until the user interacts.
          }

        } catch {
          // Do not interrupt operations
          // if the background alert poll fails.
        }
      },
      []
    );


  useEffect(() => {
    void checkActions();

    const timer =
      window.setInterval(
        () => {
          void checkActions();
        },
        5000
      );

    return () => {
      window.clearInterval(
        timer
      );
    };
  }, [checkActions]);


  if (!actionAlert) {
    return null;
  }


  return (
    <div
      className="sd-action-alert"
      role="alert"
      aria-live="assertive"
    >
      <div className="sd-action-alert-kicker">
        ● ACTION NEEDED
      </div>

      <div className="sd-action-alert-title">
        {actionAlert.title}
      </div>

      <div className="sd-action-alert-message">
        {actionAlert.message}
      </div>

      <button
        type="button"
        className="btn"
        onClick={() =>
          setActionAlert(null)
        }
      >
        Got it
      </button>
    </div>
  );
}
