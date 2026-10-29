import type {PageData, Patient} from './business';
import type {Charge} from './types';

export interface ClinicalInput {chief_complaint:string;present_illness:string;past_history:string;allergy_history:string;examination:string}
export interface ClinicalNote extends ClinicalInput {id:number;signed_at:string|null;updated_at:string}
export interface ClinicalVisit {registration_id:number;patient:Patient;record:ClinicalNote|null;locked:boolean}
export interface HistoryVisit {registration_id:number;visit_date:string;period:string;doctor_name:string;status:string;prescription_id:number|null;prescription_status:string|null;diagnosis_code:string|null;diagnosis_name:string|null;amount:string;chief_complaint:string|null;signed_at:string|null}
export interface HistoryData extends PageData<HistoryVisit> {patient:Patient}
export interface Refund {id:number;prescription_id:number;amount:string;reason:string;refunded_at:string}
export interface Receipt {receipt_no:string;prescription_no:string;patient_name:string;patient_no:string;cashier:string;charge:Charge;refund:Refund|null}
export interface BillingRecord {id:number;prescription_id:number;receipt_no:string;patient_name:string;patient_no:string;amount:string;payment_method:string;status:string;prescription_status:string;paid_at:string;cashier:string}
export interface StockAlert {id:number;generic_name:string;specification:string;stock_qty:number;available_stock:number;expiring_quantity:number;expired_quantity:number;nearest_expiry:string|null}
export interface StockMovement {id:number;drug_id:number;stock_id:number;prescription_id:number|null;kind:string;quantity_delta:number;balance_after:number;created_at:string;generic_name:string;specification:string;batch_no:string;expiry_date:string;operator:string|null}
export interface DayReport {date:string;registration_count:number;charged_amount:string;refunded_amount:string;net_amount:string;dispensed_count:number}
export interface RangeReport {start_date:string;end_date:string;days:DayReport[];totals:Omit<DayReport,'date'>;departments:{name:string;registration_count:number;charged_amount:string;refunded_amount:string;net_amount:string}[]}
