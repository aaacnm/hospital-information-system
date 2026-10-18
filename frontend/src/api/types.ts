export type Role = 'admin' | 'doctor' | 'cashier' | 'pharmacist';

export interface User {
  id: string;
  username: string;
  displayName: string;
  roles: Role[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user?: User | ApiUserPayload;
}

export interface ApiUserPayload {
  id: string | number;
  username: string;
  display_name?: string;
  displayName?: string;
  role?: Role;
  roles?: Role[];
}

export interface ApiErrorPayload {
  code?: string;
  message?: string;
  details?: unknown;
  detail?: { code?: string; message?: string } | string;
}

export interface Schedule {
  id: number;
  doctor_id: number;
  doctor_name: string;
  department_id: number;
  department_name: string;
  visit_date: string;
  period: string;
  total_quota: number;
  remain_quota: number;
  status: string;
}

export interface Registration {
  id: number;
  patient_id: number;
  doctor_id: number;
  schedule_id: number;
  queue_no: number;
  status: string;
  amount: string;
}

export interface PrescriptionItemInput {
  drug_id: number;
  quantity: number;
  dosage?: string;
  frequency?: string;
  days?: number;
}

export interface Prescription {
  id: number;
  registration_id: number;
  doctor_id: number;
  diagnosis_code: string | null;
  diagnosis_name: string | null;
  status: string;
  total_amount: string;
  items: Array<PrescriptionItemInput & { id: number; unit_price: string }>;
}

export interface Charge {
  id: number;
  prescription_id: number;
  amount: string;
  status: string;
  paid_at: string | null;
}

export interface Dispense {
  id: number;
  prescription_id: number;
  pharmacist_id: number;
  status: string;
  dispensed_at: string | null;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  before_json: string | null;
  after_json: string | null;
  ip: string | null;
  created_at: string;
}

export interface AuditLogPage {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}
