"use client";

import {
  FormEvent,
  useState,
} from "react";

import { api } from "@/lib/api";

import type {
  Supplier,
} from "@/lib/types";


export default function SupplierRegistrationForm() {
  const [message, setMessage] =
    useState("");

  const [createdSupplier, setCreatedSupplier] =
    useState<Supplier | null>(null);

  const [loading, setLoading] =
    useState(false);


  async function createSupplier(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    setLoading(true);
    setMessage("");
    setCreatedSupplier(null);

    const form =
      new FormData(event.currentTarget);

    const payload =
      Object.fromEntries(
        form.entries()
      );


    try {
      const supplier =
        await api<Supplier>(
          "/suppliers",
          {
            method: "POST",

            body: JSON.stringify({
              ...payload,

              willing_to_fulfill:
                true,
            }),
          }
        );


      setCreatedSupplier(
        supplier
      );


      setMessage(
        `${supplier.name} has been registered as Supplier #${supplier.supplier_number}.`
      );


      event.currentTarget.reset();

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Could not register supplier."
      );

    } finally {

      setLoading(false);

    }
  }


  return (
    <>

      <div className="card">

        <h2>
          Register Supplier
        </h2>

        <p className="label">
          Add a wholesaler, retailer or other
          supplier to the StoreDash network.
        </p>


        <form
          className="form-grid"
          onSubmit={
            createSupplier
          }
        >

          <label>
            Supplier / business name

            <input
              className="input"
              name="name"
              required
              placeholder="Example: Adum Wholesale Ltd."
            />
          </label>


          <label>
            Phone number

            <input
              className="input"
              name="phone"
              required
              placeholder="024..."
            />
          </label>


          <label>
            Primary StoreDash category

            <select
              className="input"
              name="category"
              required
              defaultValue=""
            >
              <option
                value=""
                disabled
              >
                Select category...
              </option>

              <option value="Provisions">
                Provisions
              </option>

              <option value="Foodstuffs">
                Foodstuffs
              </option>

              <option value="Utensils & Plastics">
                Utensils & Plastics
              </option>
            </select>
          </label>


          <label>
            Contact person

            <input
              className="input"
              name="contact_person"
              placeholder="Person StoreDash should call"
            />
          </label>


          <label>
            Town / area

            <input
              className="input"
              name="location"
              placeholder="Adum, Kejetia, Asafo..."
            />
          </label>


          <label>
            Landmark

            <input
              className="input"
              name="landmark"
              placeholder="Near Melcom, opposite station..."
            />
          </label>


          <label className="full">
            Pickup / supplier notes

            <textarea
              className="textarea"
              name="pickup_notes"
              placeholder="Where drivers should enter, loading instructions, best time to call, product categories usually stocked, etc."
            />
          </label>


          <div className="full">

            <button
              className="btn"
              disabled={
                loading
              }
            >
              {loading
                ? "Saving..."
                : "Add Supplier"}
            </button>

          </div>

        </form>


        {message && (

          <div
            className="notice"
            style={{
              marginTop: 16,
            }}
          >
            {message}
          </div>

        )}

      </div>


      {createdSupplier && (

        <div
          className="card"
          style={{
            marginTop: 18,
          }}
        >

          <div className="eyebrow">
            Supplier successfully created
          </div>

          <h2>
            Supplier #{createdSupplier.supplier_number}
          </h2>


          <dl className="details-list">

            <div>
              <dt>
                Name
              </dt>

              <dd>
                {createdSupplier.name}
              </dd>
            </div>


            <div>
              <dt>
                Phone
              </dt>

              <dd>
                {createdSupplier.phone}
              </dd>
            </div>


            <div>
              <dt>
                Category
              </dt>

              <dd>
                {createdSupplier.category || "—"}
              </dd>
            </div>


            <div>
              <dt>
                Location
              </dt>

              <dd>
                {createdSupplier.location || "—"}
              </dd>
            </div>

          </dl>

        </div>

      )}

    </>
  );
}