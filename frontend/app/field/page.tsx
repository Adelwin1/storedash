import Link from "next/link";

export default function FieldHomePage() {
  return (
    <>
      <div className="header">
        <div>
          <h1>Field Work</h1>

          <p className="label">
            Choose what you are registering today.
          </p>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gap: 16,
          gridTemplateColumns:
            "repeat(auto-fit, minmax(220px, 1fr))",
        }}
      >
        <Link
          href="/field/customers"
          className="card"
        >
          <h2>Add Customer</h2>
          <p className="label">
            Register a new StoreDash customer.
          </p>
        </Link>

        <Link
          href="/field/suppliers"
          className="card"
        >
          <h2>Add Supplier</h2>
          <p className="label">
            Register a verified supplier.
          </p>
        </Link>
      </div>
    </>
  );
}
