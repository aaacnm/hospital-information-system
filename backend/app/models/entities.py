from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class UserRole(StrEnum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    CASHIER = "cashier"
    PHARMACIST = "pharmacist"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class RegistrationStatus(StrEnum):
    PENDING = "候诊"
    PAID = "就诊中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


class PrescriptionStatus(StrEnum):
    DRAFT = "草稿"
    PENDING_CHARGE = "待收费"
    PAID = "已收费"
    DISPENSED = "已发药"
    CANCELLED = "已取消"
    REFUNDED = "已退费"


class OrderStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class BaseEntity(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(BaseEntity):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=UserRole.CASHIER.value, index=True)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)

    doctor: Mapped[Doctor | None] = relationship(back_populates="user", uselist=False)
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")


class Department(BaseEntity):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    doctors: Mapped[list[Doctor]] = relationship(back_populates="department")


class Doctor(BaseEntity):
    __tablename__ = "doctors"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    license_no: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    user: Mapped[User] = relationship(back_populates="doctor")
    department: Mapped[Department] = relationship(back_populates="doctors")
    schedules: Mapped[list[Schedule]] = relationship(back_populates="doctor")


class Patient(BaseEntity):
    __tablename__ = "patients"

    patient_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    id_no_masked: Mapped[str | None] = mapped_column(String(32))
    gender: Mapped[str | None] = mapped_column(String(10))
    birthday: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(32))

    registrations: Mapped[list[RegistrationOrder]] = relationship(back_populates="patient")


class Schedule(BaseEntity):
    __tablename__ = "schedules"
    __table_args__ = (
        UniqueConstraint("doctor_id", "visit_date", "period", name="uq_doctor_schedule"),
        CheckConstraint(
            "remain_quota >= 0 AND remain_quota <= total_quota", name="ck_schedule_quota"
        ),
    )

    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    period: Mapped[str] = mapped_column(String(20))
    total_quota: Mapped[int] = mapped_column(Integer)
    remain_quota: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")

    doctor: Mapped[Doctor] = relationship(back_populates="schedules")
    registrations: Mapped[list[RegistrationOrder]] = relationship(back_populates="schedule")


class Drug(BaseEntity):
    __tablename__ = "drugs"
    __table_args__ = (
        CheckConstraint("stock_qty >= 0", name="ck_drug_stock"),
        CheckConstraint("unit_price > 0", name="ck_drug_price"),
    )

    generic_name: Mapped[str] = mapped_column(String(120), index=True)
    trade_name: Mapped[str | None] = mapped_column(String(120))
    specification: Mapped[str] = mapped_column(String(120))
    dosage_form: Mapped[str] = mapped_column(String(40))
    insurance_type: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")

    prescription_items: Mapped[list[PrescriptionItem]] = relationship(back_populates="drug")


class DrugStock(BaseEntity):
    __tablename__ = "drug_stocks"
    __table_args__ = (
        UniqueConstraint("drug_id", "batch_no", name="uq_drug_batch"),
        CheckConstraint("quantity >= 0", name="ck_batch_quantity"),
    )

    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), index=True)
    batch_no: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column(Integer)
    expiry_date: Mapped[date] = mapped_column(Date, index=True)


class RegistrationOrder(BaseEntity):
    __tablename__ = "registration_orders"
    __table_args__ = (UniqueConstraint("schedule_id", "queue_no", name="uq_schedule_queue"),)

    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), index=True)
    queue_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=RegistrationStatus.PENDING.value)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(back_populates="registrations")
    schedule: Mapped[Schedule] = relationship(back_populates="registrations")
    prescription: Mapped[Prescription | None] = relationship(
        back_populates="registration", uselist=False
    )
    clinical_record: Mapped[ClinicalRecord | None] = relationship(
        back_populates="registration", uselist=False
    )


class Prescription(BaseEntity):
    __tablename__ = "prescriptions"

    registration_id: Mapped[int] = mapped_column(ForeignKey("registration_orders.id"), unique=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    diagnosis_code: Mapped[str | None] = mapped_column(String(32))
    diagnosis_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(
        String(20), default=PrescriptionStatus.DRAFT.value, index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    registration: Mapped[RegistrationOrder] = relationship(back_populates="prescription")
    items: Mapped[list[PrescriptionItem]] = relationship(back_populates="prescription")
    charge_order: Mapped[ChargeOrder | None] = relationship(
        back_populates="prescription", uselist=False
    )
    dispense_order: Mapped[DispenseOrder | None] = relationship(
        back_populates="prescription", uselist=False
    )

    @property
    def patient_name(self) -> str:
        return self.registration.patient.name

    @property
    def patient_no(self) -> str:
        return self.registration.patient.patient_no

    @property
    def doctor_name(self) -> str:
        return self.registration.schedule.doctor.name


class PrescriptionItem(BaseEntity):
    __tablename__ = "prescription_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_item_quantity"),)

    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    dosage: Mapped[str | None] = mapped_column(String(120))
    frequency: Mapped[str | None] = mapped_column(String(80))
    days: Mapped[int | None] = mapped_column(Integer)

    prescription: Mapped[Prescription] = relationship(back_populates="items")
    drug: Mapped[Drug] = relationship(back_populates="prescription_items")

    @property
    def drug_name(self) -> str:
        return self.drug.generic_name

    @property
    def specification(self) -> str:
        return self.drug.specification


class ChargeOrder(BaseEntity):
    __tablename__ = "charge_orders"
    __table_args__ = (Index("ix_charge_paid_at", "paid_at"),)

    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payer: Mapped[str | None] = mapped_column(String(80))
    payment_method: Mapped[str] = mapped_column(String(20), default="现金", server_default="未记录")
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    prescription: Mapped[Prescription] = relationship(back_populates="charge_order")
    refund: Mapped[RefundOrder | None] = relationship(back_populates="charge", uselist=False)


class ClinicalRecord(BaseEntity):
    __tablename__ = "clinical_records"

    registration_id: Mapped[int] = mapped_column(ForeignKey("registration_orders.id"), unique=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    chief_complaint: Mapped[str] = mapped_column(String(300))
    present_illness: Mapped[str] = mapped_column(Text)
    past_history: Mapped[str] = mapped_column(Text)
    allergy_history: Mapped[str] = mapped_column(Text)
    examination: Mapped[str] = mapped_column(Text)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    registration: Mapped[RegistrationOrder] = relationship(back_populates="clinical_record")


class RefundOrder(BaseEntity):
    __tablename__ = "refund_orders"
    __table_args__ = (Index("ix_refund_time", "refunded_at"),)

    charge_id: Mapped[int] = mapped_column(ForeignKey("charge_orders.id"), unique=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    charge: Mapped[ChargeOrder] = relationship(back_populates="refund")


class StockMovement(BaseEntity):
    __tablename__ = "stock_movements"
    __table_args__ = (
        UniqueConstraint(
            "prescription_id", "stock_id", "kind", name="uq_movement_prescription_batch_kind"
        ),
        CheckConstraint("quantity_delta != 0", name="ck_movement_nonzero"),
        CheckConstraint("balance_after >= 0", name="ck_movement_balance"),
        Index("ix_movement_drug_time", "drug_id", "created_at", "id"),
    )

    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    stock_id: Mapped[int] = mapped_column(ForeignKey("drug_stocks.id"), index=True)
    prescription_id: Mapped[int | None] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    quantity_delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    stock: Mapped[DrugStock] = relationship()


class DispenseOrder(BaseEntity):
    __tablename__ = "dispense_orders"

    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), unique=True)
    pharmacist_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.PENDING.value)
    dispensed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    prescription: Mapped[Prescription] = relationship(back_populates="dispense_order")


class AuditLog(BaseEntity):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_time_id", "created_at", "id"),)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64))

    user: Mapped[User | None] = relationship(back_populates="audit_logs")
