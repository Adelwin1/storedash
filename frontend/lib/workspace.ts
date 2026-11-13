export function workspaceForRole(
  role: string
): string {
  switch (role) {
    case "supplier_field":
      return "/field/suppliers";

    case "customer_field":
      return "/field/customers";

    case "acquisition":
      return "/field";

    case "operations":
    case "manager":
    case "admin":
      return "/dashboard";

    default:
      return "/login";
  }
}
