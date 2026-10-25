import { Suspense } from "react";
import NewOrderClient from "./NewOrderClient";

export default function NewOrderPage() {
  return (
    <Suspense
      fallback={
        <div className="card">
          Loading new order...
        </div>
      }
    >
      <NewOrderClient />
    </Suspense>
  );
}
