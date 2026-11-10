export type Role = 'admin' | 'manager' | 'agent' | 'customer';
export type CarStatus = 'available' | 'rented' | 'maintenance' | 'retired';
export type CarCategory = 'economy' | 'compact' | 'midsize' | 'suv' | 'luxury' | 'van';
export type ReservationStatus = 'pending' | 'confirmed' | 'active' | 'completed' | 'cancelled' | 'no_show';
export type Insurance = 'none' | 'basic' | 'full';
export type PaymentKind = 'payment' | 'refund' | 'deposit' | 'deposit_refund';
export type PaymentMethod = 'cash' | 'card' | 'bank_transfer';
export type MaintenanceStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export const CAR_CATEGORIES: CarCategory[] = ['economy', 'compact', 'midsize', 'suv', 'luxury', 'van'];
export const CAR_STATUSES: CarStatus[] = ['available', 'rented', 'maintenance', 'retired'];
export const RESERVATION_STATUSES: ReservationStatus[] = [
  'pending', 'confirmed', 'active', 'completed', 'cancelled', 'no_show',
];

export interface Page<T> {
  items: T[];
  total: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  branch_id: string | null;
  last_login_at: string | null;
  locked_until: string | null;
  created_at: string;
}

export interface Branch {
  id: string;
  name: string;
  address: string;
  city: string;
  phone: string;
  email: string | null;
  is_active: boolean;
}

export interface Car {
  id: string;
  branch_id: string | null;
  make: string;
  model: string;
  year: number;
  color: string;
  category: CarCategory;
  transmission: 'manual' | 'automatic';
  fuel_type: 'petrol' | 'diesel' | 'hybrid' | 'electric';
  seats: number;
  daily_rate: string;
  plate_number?: string;
  vin?: string;
  mileage?: number;
  status?: CarStatus;
  notes?: string | null;
}

export interface CarBrief {
  id: string;
  make: string;
  model: string;
  plate_number: string;
}

export interface Customer {
  id: string;
  user_id: string | null;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  date_of_birth: string;
  address: string | null;
  city: string | null;
  country: string | null;
  driver_license_number: string;
  license_country: string;
  license_expiry: string;
  id_document_number: string | null;
  is_blacklisted: boolean;
  blacklist_reason: string | null;
  notes: string | null;
  created_at: string;
}

export interface Reservation {
  id: string;
  code: string;
  status: ReservationStatus;
  customer_id: string;
  customer: Pick<Customer, 'id' | 'first_name' | 'last_name' | 'email' | 'phone'>;
  car_id: string;
  car: CarBrief;
  pickup_branch_id: string | null;
  return_branch_id: string | null;
  start_at: string;
  end_at: string;
  daily_rate: string;
  insurance: Insurance;
  gps: boolean;
  child_seat: boolean;
  additional_driver: boolean;
  estimated_total: string;
  deposit_amount: string;
  notes: string | null;
  cancel_reason: string | null;
  created_at: string;
}

export interface Quote {
  days: number;
  daily_rate: string;
  base_amount: string;
  extras_amount: string;
  subtotal: string;
  tax_amount: string;
  total: string;
  deposit: string;
  currency: string;
}

export interface Rental {
  id: string;
  reservation_id: string;
  status: 'open' | 'closed';
  checked_out_at: string;
  start_mileage: number;
  start_fuel_level: number;
  checkout_notes: string | null;
  checked_in_at: string | null;
  end_mileage: number | null;
  end_fuel_level: number | null;
  damage_notes: string | null;
  base_amount: string | null;
  extras_amount: string | null;
  late_fee: string | null;
  mileage_fee: string | null;
  fuel_fee: string | null;
  damage_fee: string | null;
  tax_amount: string | null;
  total_amount: string | null;
  reservation?: Reservation;
}

export interface Payment {
  id: string;
  reservation_id: string;
  amount: string;
  method: PaymentMethod;
  kind: PaymentKind;
  reference: string | null;
  notes: string | null;
  created_at: string;
}

export interface Balance {
  total_due: string;
  paid: string;
  balance: string;
  deposit_required: string;
  deposit_held: string;
  is_final: boolean;
}

export interface Invoice {
  company_name: string;
  currency: string;
  invoice_number: string;
  issued_at: string;
  reservation: Reservation;
  rental: Rental | null;
  line_items: { label: string; amount: string }[];
  subtotal: string;
  tax_rate: string;
  tax_amount: string;
  total: string;
  payments: Payment[];
  balance: Balance;
}

export interface Maintenance {
  id: string;
  car_id: string;
  car: CarBrief;
  type: string;
  status: MaintenanceStatus;
  description: string;
  scheduled_date: string;
  completed_date: string | null;
  cost: string;
  mileage: number | null;
  vendor: string | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  created_at: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown>;
  ip: string | null;
}

export interface DashboardStats {
  currency: string;
  cars_by_status: Record<CarStatus, number>;
  fleet_size: number;
  utilization_pct: number;
  active_rentals: number;
  overdue_rentals: number;
  pending_reservations: number;
  pickups_today: number;
  returns_today: number;
  open_maintenance: number;
  revenue_month: string;
  revenue_by_month: { month: string; amount: string }[];
  upcoming_pickups: Reservation[];
  overdue: Reservation[];
}
