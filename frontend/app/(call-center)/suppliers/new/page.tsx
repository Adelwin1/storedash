import SupplierRegistrationForm
  from "@/components/SupplierRegistrationForm";


export default function NewSupplierPage() {
  return (
    <>

      <div className="header">

        <div>

          <h1>
            Register Supplier
          </h1>

          <p className="label">
            Add a new supplier to the
            StoreDash network.
          </p>

        </div>

      </div>


      <SupplierRegistrationForm />

    </>
  );
}