"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
  useSearchParams
} from "next/navigation";

import { api } from "@/lib/api";

import type {
  Business,
  Order,
} from "@/lib/types";


type Item = {
  name: string;
  requested_quantity: number;
  unit: string;
};


export default function NewOrderPage() {
  const router = useRouter()
  const searchParams = useSearchParams();

  const [query, setQuery] =
    useState("");

  const [customers, setCustomers] =
    useState<Business[]>([]);

  const [
    selectedCustomer,
    setSelectedCustomer,
  ] = useState<Business | null>(null);

  const [items, setItems] =
    useState<Item[]>([
      {
        name: "",
        requested_quantity: 1,
        unit: "unit",
      },
    ]);

  const [message, setMessage] =
    useState("");


  useEffect(() => {
    const businessId =
      searchParams.get("business_id");

    if (!businessId) {
      return;
    }

    api<Business>(
      `/businesses/${businessId}`
    )
      .then(setSelectedCustomer)
      .catch(() =>
        setMessage(
          "Could not load that customer."
        )
      );

  }, [searchParams]);


  function updateItem(
    index: number,
    key: keyof Item,
    value: string | number
  ) {
    setItems((current) =>
      current.map(
        (item, currentIndex) =>
          currentIndex === index
            ? {
                ...item,
                [key]: value,
              }
            : item
      )
    );
  }


  function removeItem(
    index: number
  ) {
    setItems((current) =>
      current.filter(
        (_, currentIndex) =>
          currentIndex !== index
      )
    );
  }


  async function findCustomer() {
    try {
      const data =
        await api<Business[]>(
          `/businesses?q=${encodeURIComponent(query)}`
        );

      setCustomers(data);

      setMessage(
        data.length
          ? ""
          : "No matching customer. Register them from Customers first."
      );

    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Customer search failed"
      );
    }
  }


  async function submit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    /*
      IMPORTANT:
      Save the form element BEFORE await.
      This fixes the:
      "Cannot read properties of null (reading 'reset')"
      error.
    */
    const formElement =
      event.currentTarget;

    if (!selectedCustomer) {
      setMessage(
        "Select a customer before creating the order."
      );

      return;
    }


    const validItems =
      items.filter(
        (item) =>
          item.name.trim() !== "" &&
          item.requested_quantity > 0
      );


    if (validItems.length === 0) {
      setMessage(
        "Add at least one item to the order."
      );

      return;
    }


    const form =
      new FormData(formElement);


    try {
      const order =
        await api<Order>(
          "/orders",
          {
            method: "POST",

            body: JSON.stringify({
              business_id:
                selectedCustomer.id,

              notes:
                form.get("notes") ||
                null,

              items: validItems,
            }),
          }
        );


      setMessage(
        `${order.order_number} created successfully for Customer #${selectedCustomer.customer_number}.`

      );
      router.push("/dashboard");
router.refresh();

return;


      setItems([
        {
          name: "",
          requested_quantity: 1,
          unit: "unit",
        },
      ]);


      /*
        Use our saved form reference,
        NOT event.currentTarget after await.
      */
      formElement.reset();

    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create order"
      );
    }
  }


  return (
    <>
      <div className="header">
        <div>
          <h1>New Order</h1>

          <p className="label">
            Find the caller and record
            what they want to purchase.
          </p>
        </div>
      </div>


      {/* CUSTOMER */}

      <div className="card">
        <h2>
          1. Select Customer
        </h2>


        {selectedCustomer ? (
          <div className="selected-record">
            <div>
              <div className="eyebrow">
                Customer #
                {selectedCustomer.customer_number}
              </div>

              <strong>
                {selectedCustomer.business_name}
              </strong>

              <div className="label">
                {selectedCustomer.owner_name}
                {" · "}
                {selectedCustomer.phone}
              </div>
            </div>


            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setSelectedCustomer(null);
                setCustomers([]);
                setQuery("");
              }}
            >
              Change Customer
            </button>
          </div>
        ) : (
          <>
            <div className="toolbar">
              <input
                className="input"
                style={{
                  maxWidth: 560,
                }}
                value={query}
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
                    findCustomer();
                  }
                }}
                placeholder="Customer #000, name, business or phone"
              />


              <button
                type="button"
                className="btn"
                onClick={
                  findCustomer
                }
              >
                Search
              </button>
            </div>


            {customers.length > 0 && (
              <table
                className="table"
                style={{
                  marginTop: 12,
                }}
              >
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Business</th>
                    <th>Owner</th>
                    <th>Phone</th>
                    <th></th>
                  </tr>
                </thead>


                <tbody>
                  {customers.map(
                    (customer) => (
                      <tr
                        key={
                          customer.id
                        }
                      >
                        <td>
                          <span className="number-badge">
                            {customer.customer_number}
                          </span>
                        </td>

                        <td>
                          {customer.business_name}
                        </td>

                        <td>
                          {customer.owner_name}
                        </td>

                        <td>
                          {customer.phone}
                        </td>

                        <td>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => {
                              setSelectedCustomer(
                                customer
                              );

                              setCustomers(
                                []
                              );

                              setMessage(
                                ""
                              );
                            }}
                          >
                            Select
                          </button>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>


      {/* ORDER */}

      <div
        className="card"
        style={{
          marginTop: 18,
        }}
      >
        <form onSubmit={submit}>
          <h2>
            2. Requested Items
          </h2>

          <p className="label">
            Enter exactly what the
            customer tells you they need.
          </p>


          <div
            style={{
              marginTop: 18,
            }}
          >
            {items.map(
              (item, index) => (
                <div
                  key={index}
                  style={{
                    border:
                      "1px solid #e5e7eb",
                    borderRadius:
                      10,
                    padding:
                      16,
                    marginBottom:
                      12,
                  }}
                >
                  <div className="form-grid">
                    <label>
                      Item

                      <input
                        className="input"
                        value={
                          item.name
                        }
                        required
                        onChange={(
                          event
                        ) =>
                          updateItem(
                            index,
                            "name",
                            event
                              .target
                              .value
                          )
                        }
                        placeholder="Example: Milo 400g"
                      />
                    </label>


                    <label>
                      Quantity

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
                          updateItem(
                            index,
                            "requested_quantity",
                            Number(
                              event
                                .target
                                .value
                            )
                          )
                        }
                      />
                    </label>


                    <label>
                      Unit

                      <input
                        className="input"
                        value={
                          item.unit
                        }
                        onChange={(
                          event
                        ) =>
                          updateItem(
                            index,
                            "unit",
                            event
                              .target
                              .value
                          )
                        }
                        placeholder="carton, bag, bottle, unit..."
                      />
                    </label>


                    <div
                      style={{
                        display:
                          "flex",
                        alignItems:
                          "flex-end",
                      }}
                    >
                      {items.length >
                        1 && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() =>
                            removeItem(
                              index
                            )
                          }
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>


          <button
            type="button"
            className="btn btn-secondary"
            onClick={() =>
              setItems([
                ...items,

                {
                  name: "",
                  requested_quantity: 1,
                  unit: "unit",
                },
              ])
            }
          >
            + Add Item
          </button>


          <label
            style={{
              display: "block",
              marginTop: 20,
            }}
          >
            Order Notes

            <textarea
              className="textarea"
              name="notes"
              placeholder="Substitutions, urgency, customer instructions..."
            />
          </label>


          <button
            className="btn"
            style={{
              marginTop: 16,
            }}
            disabled={
              !selectedCustomer
            }
          >
            Create Draft Order
          </button>
        </form>


        {message && (
          <div className="notice">
            {message}
          </div>
        )}
      </div>
    </>
  );
}
