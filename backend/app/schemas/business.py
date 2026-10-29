from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.rules import mask_id, mask_phone


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
    model_config = ConfigDict(str_strip_whitespace=True)
    patient_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=80)
    id_no_masked: str | None = Field(default=None, max_length=32)
    gender: str | None = Field(default=None, max_length=10)
    birthday: date | None = None
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("id_no_masked")
    @classmethod
    def private_id(cls, value):
        return mask_id(value)

    @field_validator("phone")
    @classmethod
    def private_phone(cls, value):
        return mask_phone(value)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_no: str
    name: str
    id_no_masked: str | None
    gender: str | None
    birthday: date | None
    phone: str | None

    @field_validator("id_no_masked")
    @classmethod
    def private_id(cls, value):
        return mask_id(value)

    @field_validator("phone")
    @classmethod
    def private_phone(cls, value):
        return mask_phone(value)


class DrugCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
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
    available_stock: int | None = None
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
    refunded_amount: Decimal = Decimal("0.00")
    net_amount: Decimal = Decimal("0.00")


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
    model_config = ConfigDict(str_strip_whitespace=True)
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
    drug_name: str = ""
    specification: str = ""


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
    patient_name: str = ""
    patient_no: str = ""
    doctor_name: str = ""


class ChargeResponse(BaseModel):
    id: int
    prescription_id: int
    amount: Decimal
    status: str
    paid_at: datetime | None
    payment_method: str


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


class ScheduleCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    visit_date: date
    period: str = Field(pattern="^(上午|下午)$")
    total_quota: int = Field(ge=1, le=1000)


class StockCreate(BaseModel):
    batch_no: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=1000000)
    expiry_date: date


class StockResponse(StockCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    drug_id: int
    quantity: int = Field(ge=0)


class UserPatch(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码的 UTF-8 长度不能超过 72 字节")
        return value


class ClinicalRecordInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    chief_complaint: str = Field(min_length=1, max_length=300)
    present_illness: str = Field(min_length=1, max_length=2000)
    past_history: str = Field(min_length=1, max_length=1000)
    allergy_history: str = Field(min_length=1, max_length=500)
    examination: str = Field(min_length=1, max_length=1000)


class ClinicalRecordResponse(ClinicalRecordInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_id: int
    doctor_id: int
    signed_at: datetime | None
    updated_at: datetime


class ChargeInput(BaseModel):
    payment_method: Literal["现金", "银行卡", "模拟扫码"] = "现金"


class RefundInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str = Field(min_length=4, max_length=300)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    prescription_id: int
    charge_id: int
    amount: Decimal
    reason: str
    created_by: int
    refunded_at: datetime
