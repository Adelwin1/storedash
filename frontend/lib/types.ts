export type OrderItem = {
  id: number;
  name: string;
  brand?: string | null;
  size?: string | null;
  requested_quantity: number;
  unit: string;
  confirmed_quantity?: number | null;
  confirmed_price?: string | number | null;
  supplier_id?: number | null;
  availability_status: string;
};

export type Order = {
  id: number;
  order_number: string;
  business_id: number;
  operator_id?: number | null;
  status: string;
  notes?: string | null;
  goods_total: string | number;
  delivery_fee: string | number;
  service_fee: string | number;
  final_total: string | number;
  created_at: string;
  items: OrderItem[];
};

export type Business = {
  id: number;
  customer_number: string;
  owner_name: string;
  business_name: string;
  phone: string;
  alternate_phone?: string | null;
  business_type?: string | null;
  address?: string | null;
  landmark?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  delivery_instructions?: string | null;
  created_at: string;
};

export type Supplier = {
  id: number;
  supplier_number: string;
  name: string;
  category?: string | null;
  phone: string;
  contact_person?: string | null;
  location?: string | null;
  landmark?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  pickup_notes?: string | null;
  willing_to_fulfill: boolean;
  created_at: string;
};
