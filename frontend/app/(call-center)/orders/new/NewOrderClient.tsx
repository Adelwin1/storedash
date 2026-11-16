"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  LAUNCH_CATALOG,
  getMarketCategory,
  getProduct,
  getSection,
  type MarketCategoryKey,
  type SizeClass,
} from "@/lib/launchCatalog";
import type { Business, Order, OrderItem } from "@/lib/types";

type Item = {
  marketCategory: MarketCategoryKey;
  sectionKey: string;
  productId: string;
  name: string;
  brand: string;
  size: string;
  requested_quantity: number;
  unit: string;
  logisticsCategoryCode: string;
  packageType: string;
  sizeClass: SizeClass;
  physicalSizeText: string;
  variantKey: string;
};

type LogisticsCategory = {
  id: number;
  code: string;
  name: string;
};

type LogisticsType = {
  id: number;
  category_id: number;
  name: string;
  package_type: string;
  load_units: number;
};

function blankItem(): Item {
  const category = getMarketCategory("provisions");
  return {
    marketCategory: category.key,
    sectionKey: category.sections[0].key,
    productId: "",
    name: "",
    brand: "",
    size: "",
    requested_quantity: 1,
    unit: "unit",
    logisticsCategoryCode: "",
    packageType: "",
    sizeClass: "medium",
    physicalSizeText: "",
    variantKey: "",
  };
}

function sameSavedItem(saved: OrderItem, requested: Item) {
  return (
    saved.name === requested.name
    && saved.unit === requested.unit
    && Math.abs(
      Number(saved.requested_quantity)
      - requested.requested_quantity
    ) < 0.0001
  );
}

export default function NewOrderPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState("");
  const [customers, setCustomers] = useState<Business[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Business | null>(null);
  const [items, setItems] = useState<Item[]>([blankItem()]);
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const businessId = searchParams.get("business_id");
    if (!businessId) return;

    api<Business>(`/businesses/${businessId}`)
      .then(setSelectedCustomer)
      .catch(() =>
        setMessage("Could not load that customer.")
      );
  }, [searchParams]);

  function patchItem(index: number, patch: Partial<Item>) {
    setItems((current) =>
      current.map((item, i) =>
        i === index
          ? { ...item, ...patch }
          : item
      )
    );
  }

  function chooseCategory(index: number, key: MarketCategoryKey) {
    const category = getMarketCategory(key);
    const quantity = items[index].requested_quantity;

    patchItem(index, {
      ...blankItem(),
      requested_quantity: quantity,
      marketCategory: category.key,
      sectionKey: category.sections[0].key,
    });
  }

  function chooseSection(index: number, sectionKey: string) {
    patchItem(index, {
      sectionKey,
      productId: "",
      name: "",
      brand: "",
      size: "",
      unit: "unit",
      logisticsCategoryCode: "",
      packageType: "",
      sizeClass: "medium",
      physicalSizeText: "",
      variantKey: "",
    });
  }

  function chooseProduct(index: number, productId: string) {
    const currentItem = items[index];
    const selected = getProduct(
      currentItem.marketCategory,
      currentItem.sectionKey,
      productId,
    );

    if (!selected) {
      patchItem(index, {
        productId: "",
        name: "",
      });
      return;
    }

    const option = selected.packages[0];

    patchItem(index, {
      productId: selected.id,
      name: selected.name,
      brand: "",
      size: option.physicalSizeText,
      unit: option.unit,
      logisticsCategoryCode: selected.logisticsCategoryCode,
      packageType: option.packageType,
      sizeClass: option.sizeClass,
      physicalSizeText: option.physicalSizeText,
      variantKey: option.variantKey,
    });
  }

  function choosePackage(index: number, packageIndex: number) {
    const currentItem = items[index];
    const selected = getProduct(
      currentItem.marketCategory,
      currentItem.sectionKey,
      currentItem.productId,
    );
    const option = selected?.packages[packageIndex];

    if (!option) return;

    patchItem(index, {
      size: option.physicalSizeText,
      unit: option.unit,
      packageType: option.packageType,
      sizeClass: option.sizeClass,
      physicalSizeText: option.physicalSizeText,
      variantKey: option.variantKey,
    });
  }

  async function findCustomer() {
    try {
      const data = await api<Business[]>(
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

  async function applyAutomaticLogistics(
    order: Order,
    requestedItems: Item[],
  ) {
    const categories = await api<LogisticsCategory[]>(
      "/logistics/categories"
    );

    const byCode = new Map(
      categories.map((category) => [
        category.code,
        category,
      ])
    );

    const typeCache = new Map<number, LogisticsType[]>();
    const usedSavedIds = new Set<number>();

    for (const requested of requestedItems) {
      const category = byCode.get(
        requested.logisticsCategoryCode
      );

      if (!category) {
        throw new Error(
          `Logistics setup is missing '${requested.logisticsCategoryCode}'. Ask an admin to run the production logistics seed.`
        );
      }

      let types = typeCache.get(category.id);

      if (!types) {
        types = await api<LogisticsType[]>(
          `/logistics/types?category_id=${category.id}`
        );

        typeCache.set(category.id, types);
      }

      const logisticsType = types.find(
        (row) =>
          row.package_type === requested.packageType
      );

      if (!logisticsType) {
        throw new Error(
          `Logistics package '${requested.packageType}' is not configured for ${requested.name}.`
        );
      }

      const savedItem =
        order.items.find(
          (row) =>
            !usedSavedIds.has(row.id)
            && sameSavedItem(row, requested)
        )
        ?? order.items.find(
          (row) =>
            !usedSavedIds.has(row.id)
        );

      if (!savedItem) {
        throw new Error(
          `Could not match ${requested.name} to the saved order item.`
        );
      }

      usedSavedIds.add(savedItem.id);

      await api(
        `/orders/${order.id}/items/${savedItem.id}/logistics`,
        {
          method: "PUT",
          body: JSON.stringify({
            category_id: category.id,
            logistics_type_id: logisticsType.id,
            size_class: requested.sizeClass,
            variant_key: requested.variantKey,
            physical_size_text: requested.physicalSizeText,
          }),
        }
      );
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedCustomer) {
      setMessage(
        "Select a customer before creating the order."
      );
      return;
    }

    const validItems = items.filter(
      (item) =>
        item.productId
        && item.name.trim()
        && item.requested_quantity > 0
    );

    if (validItems.length !== items.length) {
      setMessage(
        "Choose a catalog product and package/size for every order line."
      );
      return;
    }

    const form = new FormData(event.currentTarget);

    try {
      setCreating(true);
      setMessage(
        "Creating order and assigning logistics automatically..."
      );

      const order = await api<Order>(
        "/orders",
        {
          method: "POST",
          body: JSON.stringify({
            business_id: selectedCustomer.id,
            notes: form.get("notes") || null,
            items: validItems.map((item) => ({
              name: item.name,
              brand: item.brand.trim() || null,
              size: item.size,
              requested_quantity: item.requested_quantity,
              unit: item.unit,
            })),
          }),
        }
      );

      await applyAutomaticLogistics(
        order,
        validItems,
      );

      setMessage(
        `${order.order_number} created and logistics assigned automatically.`
      );

      router.push(
        `/orders/${order.id}`
      );
      router.refresh();

    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Could not create order"
      );

    } finally {
      setCreating(false);
    }
  }

  const deliveryConfirmed = Boolean(
    selectedCustomer
      && selectedCustomer.latitude != null
      && selectedCustomer.longitude != null
  );

  return (
    <>
      <div className="header">
        <div>
          <h1>New Order</h1>
          <p className="label">
            Choose products from the launch catalog. StoreDash assigns weight, load and delivery logistics automatically.
          </p>
        </div>
      </div>

      <div className="card">
        <h2>1. Select Customer</h2>

        {selectedCustomer ? (
          <>
            <div className="selected-record">
              <div>
                <div className="eyebrow">
                  Customer #{selectedCustomer.customer_number}
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

            <div
              style={{
                marginTop: 14,
                padding: 14,
                borderRadius: 10,
                border: deliveryConfirmed
                  ? "1px solid #bbf7d0"
                  : "1px solid #fde68a",
                background: deliveryConfirmed
                  ? "#f0fdf4"
                  : "#fffbeb",
              }}
            >
              <strong>
                Delivery information
              </strong>

              <div
                className="label"
                style={{ marginTop: 6 }}
              >
                <div>
                  Address: {selectedCustomer.address || "Not recorded"}
                </div>
                <div>
                  Landmark: {selectedCustomer.landmark || "Not recorded"}
                </div>
                <div>
                  Instructions: {selectedCustomer.delivery_instructions || "None"}
                </div>
                <div>
                  Map location: {deliveryConfirmed ? "Confirmed" : "Not confirmed yet"}
                </div>
              </div>

              {!deliveryConfirmed && (
                <div style={{ marginTop: 8 }}>
                  <Link
                    href={`/customers/${selectedCustomer.id}`}
                  >
                    Confirm the delivery location before generating the final quote.
                  </Link>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="toolbar">
              <input
                className="input"
                style={{ maxWidth: 560 }}
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    findCustomer();
                  }
                }}
                placeholder="Customer #000, name, business or phone"
              />

              <button
                type="button"
                className="btn"
                onClick={findCustomer}
              >
                Search
              </button>
            </div>

            {customers.length > 0 && (
              <table
                className="table"
                style={{ marginTop: 12 }}
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
                  {customers.map((customer) => (
                    <tr key={customer.id}>
                      <td>
                        <span className="number-badge">
                          {customer.customer_number}
                        </span>
                      </td>
                      <td>{customer.business_name}</td>
                      <td>{customer.owner_name}</td>
                      <td>{customer.phone}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => {
                            setSelectedCustomer(customer);
                            setCustomers([]);
                            setMessage("");
                          }}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>

      <div
        className="card"
        style={{ marginTop: 18 }}
      >
        <form onSubmit={submit}>
          <h2>2. Requested Items</h2>

          <p className="label">
            Choose category → section → product → package/size. Do not estimate logistics manually.
          </p>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginTop: 12,
            }}
          >
            {LAUNCH_CATALOG.map((category) => (
              <span
                key={category.key}
                style={{
                  border:
                    "1px solid "
                    + category.accent
                    + "33",
                  background: category.soft,
                  color: category.accent,
                  borderRadius: 999,
                  padding: "6px 10px",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {category.label}
              </span>
            ))}
          </div>

          <div style={{ marginTop: 18 }}>
            {items.map((item, index) => {
              const category =
                getMarketCategory(
                  item.marketCategory
                );

              const section =
                getSection(
                  item.marketCategory,
                  item.sectionKey
                );

              const selectedProduct =
                getProduct(
                  item.marketCategory,
                  item.sectionKey,
                  item.productId
                );

              const packageIndex =
                selectedProduct
                  ? Math.max(
                      0,
                      selectedProduct.packages.findIndex(
                        (entry) =>
                          entry.variantKey
                          === item.variantKey
                      )
                    )
                  : 0;

              return (
                <div
                  key={index}
                  style={{
                    border:
                      "1px solid "
                      + category.accent
                      + "33",
                    borderLeft:
                      "5px solid "
                      + category.accent,
                    background:
                      category.soft,
                    borderRadius: 12,
                    padding: 16,
                    marginBottom: 14,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      alignItems: "center",
                      marginBottom: 12,
                    }}
                  >
                    <strong>
                      Item {index + 1}
                    </strong>

                    {items.length > 1 && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() =>
                          setItems((currentItems) =>
                            currentItems.filter(
                              (_, i) =>
                                i !== index
                            )
                          )
                        }
                      >
                        Remove
                      </button>
                    )}
                  </div>

                  <div className="form-grid">
                    <label>
                      Market category

                      <select
                        className="input"
                        value={item.marketCategory}
                        onChange={(event) =>
                          chooseCategory(
                            index,
                            event.target.value as MarketCategoryKey
                          )
                        }
                      >
                        {LAUNCH_CATALOG.map((entry) => (
                          <option
                            key={entry.key}
                            value={entry.key}
                          >
                            {entry.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Section

                      <select
                        className="input"
                        value={item.sectionKey}
                        onChange={(event) =>
                          chooseSection(
                            index,
                            event.target.value
                          )
                        }
                      >
                        {category.sections.map((entry) => (
                          <option
                            key={entry.key}
                            value={entry.key}
                          >
                            {entry.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Product

                      <select
                        className="input"
                        required
                        value={item.productId}
                        onChange={(event) =>
                          chooseProduct(
                            index,
                            event.target.value
                          )
                        }
                      >
                        <option value="">
                          Select product...
                        </option>

                        {section.products.map((entry) => (
                          <option
                            key={entry.id}
                            value={entry.id}
                          >
                            {entry.name}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Package / size

                      <select
                        className="input"
                        disabled={!selectedProduct}
                        value={packageIndex}
                        onChange={(event) =>
                          choosePackage(
                            index,
                            Number(event.target.value)
                          )
                        }
                      >
                        {selectedProduct?.packages.map(
                          (entry, i) => (
                            <option
                              key={entry.variantKey}
                              value={i}
                            >
                              {entry.label}
                            </option>
                          )
                        )}
                      </select>
                    </label>

                    <label>
                      Brand / preference

                      <input
                        className="input"
                        value={item.brand}
                        onChange={(event) =>
                          patchItem(
                            index,
                            {
                              brand:
                                event.target.value,
                            }
                          )
                        }
                        placeholder="Optional: preferred brand"
                      />
                    </label>

                    <label>
                      Quantity

                      <input
                        className="input"
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={item.requested_quantity}
                        onChange={(event) =>
                          patchItem(
                            index,
                            {
                              requested_quantity:
                                Number(
                                  event.target.value
                                ),
                            }
                          )
                        }
                      />
                    </label>
                  </div>

                  {selectedProduct && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: 10,
                        background: "#ffffffaa",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    >
                      <strong>
                        Automatic logistics:
                      </strong>
                      {" "}
                      {item.name}
                      {item.size
                        ? " · " + item.size
                        : ""}
                      {" · "}
                      {item.packageType}
                      {" · "}
                      weight, volume, load and delivery pricing are assigned by StoreDash.
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() =>
              setItems((currentItems) => [
                ...currentItems,
                blankItem(),
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
            style={{ marginTop: 16 }}
            disabled={
              !selectedCustomer
              || creating
            }
          >
            {creating
              ? "Creating & classifying..."
              : "Create Draft Order"}
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
