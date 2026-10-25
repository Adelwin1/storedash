import SupplierRegistrationForm
  from "@/components/SupplierRegistrationForm";


export default function FieldSuppliersPage() {
  return (
    <>

      <div className="header">

        <div>

          <h1>
            Add Supplier
          </h1>

          <p className="label">
            Register wholesalers and retailers
            you have verified in the field.
          </p>

        </div>

      </div>


      <SupplierRegistrationForm />

    </>
  );
}