from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ScheduleResponse(BaseModel):
    id: int
    doctor_id: int
    doctor_name: str
    department_id: int
    department_name: str
    visit_date: date
    period: str
    total_quota: int
    remain_quota: int
    status: str


class PatientCreate(BaseModel):
    patient_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=80)
    id_no_masked: str | None = Field(default=None, max_length=32)
    gender: str | None = Field(default=None, max_length=10)
    birthday: date | None = None
    phone: str | None = Field(default=None, max_length=32)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_no: str
    name: str
    id_no_masked: str | None
    gender: str | None
    birthday: date | None
    phone: str | None


class DrugCreate(BaseModel):
    generic_name: str = Field(min_length=1, max_length=120)
    trade_name: str | None = Field(default=None, max_length=120)
    specification: str = Field(min_length=1, max_length=120)
    dosage_form: str = Field(min_length=1, max_length=40)
    insurance_type: str | None = Field(default=None, max_length=40)
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    stock_qty: int = Field(default=0, ge=0, le=1_000_000)
    expiry_date: date | None = None


class DrugResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generic_name: str
    trade_name: str | None
    specification: str
    dosage_form: str
    insurance_type: str | None
    unit_price: Decimal
    stock_qty: int
    expiry_date: date | None
    status: str


class DrugPricePatch(BaseModel):
    unit_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class DrugImportError(BaseModel):
    row: int
    reason: str


class DrugImportResponse(BaseModel):
    total: int
    success: int
    failure: int
    errors: list[DrugImportError]


class ReportTodayResponse(BaseModel):
    date: date
    registration_count: int
    charged_amount: Decimal
    dispensed_count: int


class RegistrationCreate(BaseModel):
    patient_id: int = Field(gt=0)
    schedule_id: int = Field(gt=0)


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    schedule_id: int
    queue_no: int
    status: str
    amount: Decimal


class PrescriptionItemCreate(BaseModel):
    drug_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=1000)
    dosage: str | None = Field(default=None, max_length=120)
    frequency: str | None = Field(default=None, max_length=80)
    days: int | None = Field(default=None, gt=0, le=365)


class PrescriptionCreate(BaseModel):
    registration_id: int = Field(gt=0)
    diagnosis_code: str = Field(min_length=1, max_length=32)
    diagnosis_name: str = Field(min_length=1, max_length=120)
    items: list[PrescriptionItemCreate] = Field(min_length=1, max_length=50)


class PrescriptionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drug_id: int
    quantity: int
    unit_price: Decimal
    dosage: str | None
    frequency: str | None
    days: int | None


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_id: int
    doctor_id: int
    diagnosis_code: str | None
    diagnosis_name: str | None
    status: str
    total_amount: Decimal
    items: list[PrescriptionItemResponse]


class ChargeResponse(BaseModel):
    id: int
    prescription_id: int
    amount: Decimal
    status: str
    paid_at: datetime | None


class DispenseResponse(BaseModel):
    id: int
    prescription_id: int
    pharmacist_id: int
    status: str
    dispensed_at: datetime | None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    before_json: str | None
    after_json: str | None
    ip: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
