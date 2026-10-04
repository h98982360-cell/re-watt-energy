const API_ROOT = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "supplier" | "buyer" | "admin";
  status: string;
  is_verified: boolean;
  business_name?: string | null;
  county?: string | null;
};

export type Material = {
  id: number;
  slug: string;
  name: string;
  description?: string | null;
  typical_conditions: string[];
  typical_units: string[];
  primary_uses: string[];
  buyer_types: string[];
};

export type Listing = {
  id: number;
  supplier_id: number;
  supplier_name: string;
  material_id: number;
  material: string;
  title: string;
  condition: string;
  quantity: number;
  quantity_available: number;
  unit: string;
  price_per_unit: number | null;
  currency: string;
  county: string | null;
  city: string | null;
  description: string | null;
  status: string;
};

export type Requirement = {
  id: number;
  buyer_id: number;
  material_id: number;
  material: string;
  title: string;
  quantity: number;
  unit: string;
  acceptable_conditions: string[];
  delivery_counties: string[];
  target_price_per_unit: number | null;
  required_by: string | null;
  intended_use: string | null;
  description: string | null;
  status: string;
};

export type Match = {
  id: number;
  requirement_id: number;
  status: string;
  requested_quantity_base: number;
  matched_quantity_base: number;
  supplier_count: number;
  coverage_percent: number;
  quantity_sufficient: boolean;
  material_compatible: boolean;
  condition_compatible: boolean;
  shortfall: number;
  surplus: number;
  explanation: string | null;
  requested_quantity: number;
  matched_quantity: number;
  unit: string;
  base_unit: string;
  items: Array<{
    listing_id: number;
    supplier_id: number;
    supplier_name: string;
    title: string;
    quantity_base: string;
    quantity: string;
    unit: string;
    condition: string;
    county: string | null;
    response_status: string;
  }>;
};

export type Transaction = {
  id: number;
  match_id: number;
  material: string;
  supplier_id: number;
  supplier_name: string;
  buyer_id: number;
  buyer_name: string;
  quantity_declared: number;
  quantity_received: number | null;
  unit: string;
  unit_price: number;
  subtotal: number;
  platform_fee: number;
  total: number;
  currency: string;
  status: string;
  payments: Array<{ id: number; status: string; method: string; reference: string | null }>;
};

export type Category = {
  id: number;
  name: string;
  materials: Material[];
};

export type AIResponse<T> = {
  available: boolean;
  data?: T;
  message?: string;
};

export type MaterialInsight = {
  potential_uses: string[];
  potential_buyer_types: string[];
  important_characteristics: string[];
  summary: string;
  confidence: "low" | "medium" | "high";
  material: string;
  disclaimer: string;
};

export type CompatibilityInsight = {
  reasons: string[];
  considerations: string[];
  summary: string;
  compatibility: "high" | "partial" | "low";
};

export async function api<T>(
  path: string,
  options: RequestInit = {},
  token: string | null = null,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
  } catch {
    throw new Error("Could not reach the Re-Watt API. Please check your connection and try again.");
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    if (response.status === 401) {
      throw new Error("Your session has expired. Please log in again.");
    }
    if (response.status === 403) {
      throw new Error("You do not have permission to perform this action.");
    }
    if (response.status === 409) {
      if (payload?.detail?.toLowerCase().includes("email or phone")) {
        throw new Error("This email or phone is already registered. Please log in or use different details.");
      }
      throw new Error("This action conflicts with the current marketplace state. Refresh and try again.");
    }
    if (response.status === 422) {
      throw new Error(payload?.detail || "Please check the information and try again.");
    }
    throw new Error("Something went wrong. Please try again.");
  }
  return (await response.json()) as T;
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}
