export interface PageData<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
}
export interface Directory {
    date: string;
    departments: {
        id: number;
        name: string;
    }[];
    doctors: {
        id: number;
        name: string;
        department_id: number;
    }[];
}
export interface Patient {
    id: number;
    patient_no: string;
    name: string;
    gender: string | null;
    phone: string | null;
    id_no_masked: string | null;
}
export interface Drug {
    id: number;
    generic_name: string;
    trade_name: string | null;
    specification: string;
    dosage_form: string;
    insurance_type: string | null;
    unit_price: string;
    stock_qty: number;
    available_stock?: number | null;
    expiry_date: string | null;
}
export interface Stock {
    id: number;
    drug_id: number;
    batch_no: string;
    quantity: number;
    expiry_date: string;
}
export interface Visit {
    id: number;
    patient_id: number;
    patient_name: string;
    patient_no: string;
    doctor_name: string;
    visit_date: string;
    period: string;
    queue_no: number;
    status: string;
    prescription_id: number | null;
}
export interface Report {
    date: string;
    registration_count: number;
    charged_amount: string;
    dispensed_count: number;
}
export interface Account {
    id: number;
    username: string;
    display_name: string;
    role: string;
    status: string;
}
