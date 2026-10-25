"use client";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import {
  useParams,
} from "next/navigation";

import { api } from "@/lib/api";

import CustomerPurchaseInsights from "@/components/CustomerPurchaseInsights";

import LocationPicker from "@/components/LocationPicker";

import type {
  Business,
  Order,
  Supplier,
} from "@/lib/types";


type PairedSupplier = {
  relationship_id: number;
  supplier_id: number;
  supplier_number: string;
  name: string;
  category: string | null;
  phone: string;
  contact_person: string | null;
  location: string | null;
  is_usual: boolean;
  notes: string | null;
};


export default function CustomerProfilePage() {
  const params =
    useParams<{
      id: string;
    }>();


  const [customer, setCustomer] =
    useState<Business | null>(null);

  const [orders, setOrders] =
    useState<Order[]>([]);

  const [
    pairedSuppliers,
    setPairedSuppliers,
  ] = useState<
    PairedSupplier[]
  >([]);

  const [
    supplierResults,
    setSupplierResults,
  ] = useState<
    Supplier[]
  >([]);

  const [
    supplierSearch,
    setSupplierSearch,
  ] = useState("");

  const [loading, setLoading] =
    useState(true);

  const [
    searching,
    setSearching,
  ] = useState(false);

  const [message, setMessage] =
    useState("");

  const [error, setError] =
    useState("");


  async function loadCustomer() {
    try {
      setLoading(true);

      const [
        customerData,
        orderData,
        pairData,
      ] = await Promise.all([
        api<Business>(
          `/businesses/${params.id}`
        ),

        api<Order[]>(
          `/orders?business_id=${params.id}`
        ),

        api<PairedSupplier[]>(
          `/businesses/${params.id}/suppliers`
        ),
      ]);


      setCustomer(
        customerData
      );

      setOrders(
        orderData
      );

      setPairedSuppliers(
        pairData
      );

      setError("");

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not load customer."
      );

    } finally {
      setLoading(false);
    }
  }


  async function loadPairedSuppliers() {
    const data =
      await api<
        PairedSupplier[]
      >(
        `/businesses/${params.id}/suppliers`
      );

    setPairedSuppliers(
      data
    );
  }


  useEffect(() => {
    if (params.id) {
      loadCustomer();
    }

  }, [params.id]);


  async function searchSuppliers() {
    const query =
      supplierSearch.trim();

    if (!query) {
      setSupplierResults([]);
      return;
    }


    try {
      setSearching(true);

      const data =
        await api<
          Supplier[]
        >(
          `/suppliers?q=${encodeURIComponent(
            query
          )}`
        );


      setSupplierResults(
        data
      );

      setError("");

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not search suppliers."
      );

    } finally {
      setSearching(false);
    }
  }


  async function pairSupplier(
    supplier: Supplier
  ) {
    try {
      await api(
        `/businesses/${params.id}/suppliers/${supplier.id}`,
        {
          method: "POST",
        }
      );


      await loadPairedSuppliers();


      setMessage(
        `${supplier.name} added as a usual supplier.`
      );


      setSupplierResults(
        (current) =>
          current.filter(
            (item) =>
              item.id !==
              supplier.id
          )
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not pair supplier."
      );
    }
  }


  async function removeSupplier(
    supplier: PairedSupplier
  ) {
    const confirmed =
      window.confirm(
        `Remove ${supplier.name} from this customer's usual suppliers?`
      );

    if (!confirmed) {
      return;
    }


    try {
      await api(
        `/businesses/${params.id}/suppliers/${supplier.supplier_id}`,
        {
          method: "DELETE",
        }
      );


      await loadPairedSuppliers();


      setMessage(
        `${supplier.name} removed from usual suppliers.`
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Could not remove supplier."
      );
    }
  }


  function alreadyPaired(
    supplierId: number
  ) {
    return pairedSuppliers.some(
      (supplier) =>
        supplier.supplier_id ===
        supplierId
    );
  }


  if (loading) {
    return (
      <div className="card">
        Loading customer...
      </div>
    );
  }


  if (!customer) {
    return (
      <div className="card">
        {error ||
          "Customer not found."}
      </div>
    );
  }


  return (
    <>
      <div className="header">
        <div>
          <div className="eyebrow">
            Customer #
            {
              customer.customer_number
            }
          </div>

          <h1>
            {
              customer.business_name
            }
          </h1>

          <p className="label">
            {
              customer.owner_name
            }
          </p>
        </div>


        <div
          style={{
            display: "flex",
            gap: 10,
          }}
        >
          <Link
            href={`/orders/new?business_id=${customer.id}`}
            className="btn"
          >
            New Order
          </Link>

          <Link
            href="/customers"
            className="btn btn-secondary"
          >
            Customers
          </Link>
        </div>
      </div>


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


      <div className="grid grid-2">
        <div className="card">
          <h2>
            Customer Details
          </h2>

          <div className="details-list">
            <div>
              <span className="label">
                Owner
              </span>

              <div>
                {
                  customer.owner_name
                }
              </div>
            </div>


            <div>
              <span className="label">
                Phone
              </span>

              <div>
                {
                  customer.phone
                }
              </div>
            </div>


            <div>
              <span className="label">
                Alternate Phone
              </span>

              <div>
                {
                  customer.alternate_phone ||
                  "—"
                }
              </div>
            </div>


            <div>
              <span className="label">
                Address
              </span>

              <div>
                {
                  customer.address ||
                  "—"
                }
              </div>
            </div>


            <div>
              <span className="label">
                Landmark
              </span>

              <div>
                {
                  customer.landmark ||
                  "—"
                }
              </div>
            </div>


            <div>
              <span className="label">
                Delivery Instructions
              </span>

              <div>
                {
                  customer.delivery_instructions ||
                  "—"
                }
              </div>
            </div>
          </div>
        </div>


        <div className="card">
          <h2>
            Usual Suppliers
          </h2>

          <p className="label">
            Suppliers this customer
            normally buys from.
          </p>


          {pairedSuppliers.length ===
          0 ? (
            <div
              className="empty-state"
              style={{
                marginTop: 14,
              }}
            >
              No usual suppliers paired
              yet.
            </div>
          ) : (
            <div
              style={{
                marginTop: 14,
              }}
            >
              {pairedSuppliers.map(
                (supplier) => (
                  <div
                    key={
                      supplier.relationship_id
                    }
                    style={{
                      border:
                        "1px solid #e5e7eb",
                      borderRadius: 10,
                      padding: 14,
                      marginBottom: 10,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent:
                          "space-between",
                        alignItems:
                          "center",
                        gap: 12,
                      }}
                    >
                      <div>
                        <strong>
                          {
                            supplier.name
                          }
                        </strong>

                        <div className="label">
                          Supplier #
                          {
                            supplier.supplier_number
                          }
                        </div>

                        <div className="label">
                          {
                            supplier.phone
                          }
                        </div>

                        {supplier.location && (
                          <div className="label">
                            {
                              supplier.location
                            }
                          </div>
                        )}
                      </div>


                      <button
                        className="btn btn-secondary"
                        onClick={() =>
                          removeSupplier(
                            supplier
                          )
                        }
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                )
              )}
            </div>
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
          Pair Supplier
        </h2>

        <p className="label">
          Search suppliers collected by
          the field team using supplier
          number, name, phone, contact
          person or category.
        </p>


        <div
          style={{
            display: "flex",
            gap: 10,
            marginTop: 14,
            maxWidth: 700,
          }}
        >
          <input
            className="input"
            value={
              supplierSearch
            }
            onChange={(event) =>
              setSupplierSearch(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key ===
                "Enter"
              ) {
                searchSuppliers();
              }
            }}
            placeholder="Supplier name, number or phone"
          />

          <button
            className="btn"
            onClick={
              searchSuppliers
            }
            disabled={
              searching
            }
          >
            {searching
              ? "Searching..."
              : "Search"}
          </button>
        </div>


        {supplierResults.length >
          0 && (
          <table
            className="table"
            style={{
              marginTop: 18,
            }}
          >
            <thead>
              <tr>
                <th>
                  Supplier
                </th>

                <th>
                  Category
                </th>

                <th>
                  Phone
                </th>

                <th>
                  Location
                </th>

                <th></th>
              </tr>
            </thead>


            <tbody>
              {supplierResults.map(
                (supplier) => {
                  const paired =
                    alreadyPaired(
                      supplier.id
                    );


                  return (
                    <tr
                      key={
                        supplier.id
                      }
                    >
                      <td>
                        <strong>
                          {
                            supplier.name
                          }
                        </strong>

                        <div className="label">
                          Supplier #
                          {
                            supplier.supplier_number
                          }
                        </div>
                      </td>

                      <td>
                        {
                          supplier.category ||
                          "—"
                        }
                      </td>

                      <td>
                        {
                          supplier.phone
                        }
                      </td>

                      <td>
                        {
                          supplier.location ||
                          "—"
                        }
                      </td>

                      <td>
                        {paired ? (
                          <span className="badge">
                            PAIRED
                          </span>
                        ) : (
                          <button
                            className="btn btn-secondary"
                            onClick={() =>
                              pairSupplier(
                                supplier
                              )
                            }
                          >
                            Pair Supplier
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                }
              )}
            </tbody>
          </table>
        )}
      </div>


      <div
        className="card"
        style={{
          marginTop: 18,
        }}
      >
        <LocationPicker
          entityType="business"
          entityId={customer.id}
          initialLocation={
            customer.address
          }
          onSaved={(address) => {
            setCustomer({
              ...customer,
              address,
            });
          }}
        />
      </div>


      <CustomerPurchaseInsights
        businessId={customer.id}
      />



      <div
        className="card"
        style={{
          marginTop: 20,
        }}
      >
        <h2>
          Transaction History
        </h2>

        <p className="label">
          Complete StoreDash order
          history for this customer.
        </p>


        {orders.length === 0 ? (
          <div
            className="empty-state"
            style={{
              marginTop: 14,
            }}
          >
            No orders yet.
          </div>
        ) : (
          <table
            className="table"
            style={{
              marginTop: 14,
            }}
          >
            <thead>
              <tr>
                <th>
                  Order
                </th>

                <th>
                  Day #
                </th>

                <th>
                  Items
                </th>

                <th>
                  Status
                </th>

                <th>
                  Created
                </th>

                <th></th>
              </tr>
            </thead>


            <tbody>
              {orders.map(
                (order) => (
                  <tr
                    key={
                      order.id
                    }
                  >
                    <td>
                      <strong>
                        {
                          order.order_number
                        }
                      </strong>
                    </td>

                    <td>
                      #
                      {
                        (
                          order as Order & {
                            daily_number?:
                              number | null;
                          }
                        ).daily_number ??
                        "—"
                      }
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
                      {new Date(
                        order.created_at
                      ).toLocaleString()}
                    </td>

                    <td>
                      <Link
                        href={
                          `/orders/${order.id}`
                        }
                        className="btn btn-secondary"
                      >
                        View
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
