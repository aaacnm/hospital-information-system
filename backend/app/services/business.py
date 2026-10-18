from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AuditLog,
    ChargeOrder,
    DispenseOrder,
    Doctor,
    Drug,
    Patient,
    Prescription,
    PrescriptionItem,
    RegistrationOrder,
    Schedule,
    User,
)
from app.models.entities import OrderStatus, PrescriptionStatus, RegistrationStatus
from app.schemas.business import DrugCreate, PatientCreate, PrescriptionCreate, RegistrationCreate


def _error(code: str, message: str, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def _audit(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: int | str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            before_json=json.dumps(before, ensure_ascii=False) if before else None,
            after_json=json.dumps(after, ensure_ascii=False) if after else None,
        )
    )


def list_schedules(db: Session, dept_id: int | None, visit_date: date) -> list[Schedule]:
    query = (
        db.query(Schedule)
        .options(joinedload(Schedule.doctor).joinedload(Doctor.department))
        .filter(Schedule.visit_date == visit_date, Schedule.status == "active")
    )
    if dept_id is not None:
        query = query.filter(Schedule.doctor.has(department_id=dept_id))
    return query.order_by(Schedule.period, Schedule.id).all()


def list_patients(db: Session, keyword: str | None = None) -> list[Patient]:
    query = db.query(Patient)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter((Patient.patient_no.like(pattern)) | (Patient.name.like(pattern)))
    return query.order_by(Patient.id.desc()).limit(100).all()


def create_patient(db: Session, payload: PatientCreate, user: User) -> Patient:
    if db.query(Patient).filter(Patient.patient_no == payload.patient_no).first() is not None:
        raise _error("PATIENT_EXISTS", "患者编号已存在", status.HTTP_409_CONFLICT)
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.flush()
    _audit(
        db,
        user.id,
        "patient.create",
        "patient",
        patient.id,
        after={"patient_no": patient.patient_no},
    )
    db.commit()
    db.refresh(patient)
    return patient


def list_drugs(db: Session, keyword: str | None = None) -> list[Drug]:
    query = db.query(Drug).filter(Drug.status == "active")
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter((Drug.generic_name.like(pattern)) | (Drug.trade_name.like(pattern)))
    return query.order_by(Drug.id.desc()).limit(100).all()


def create_drug(db: Session, payload: DrugCreate, user: User) -> Drug:
    drug = Drug(**payload.model_dump())
    db.add(drug)
    db.flush()
    _audit(db, user.id, "drug.create", "drug", drug.id, after={"generic_name": drug.generic_name})
    db.commit()
    db.refresh(drug)
    return drug


def patch_drug_price(db: Session, drug_id: int, unit_price: Decimal, user: User) -> Drug:
    drug = db.query(Drug).filter(Drug.id == drug_id).with_for_update().first()
    if drug is None:
        raise _error("DRUG_NOT_FOUND", "药品不存在", status.HTTP_404_NOT_FOUND)
    before = {"unit_price": str(drug.unit_price)}
    drug.unit_price = unit_price
    db.flush()
    _audit(
        db,
        user.id,
        "drug.price.update",
        "drug",
        drug.id,
        before,
        {"unit_price": str(unit_price)},
    )
    db.commit()
    db.refresh(drug)
    return drug


def import_drugs(db: Session, content: bytes, user: User) -> dict:
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            decoded = content.decode("gbk")
        except UnicodeDecodeError:
            raise _error(
                "CSV_ENCODING", "CSV 必须使用 UTF-8 或 GBK 编码", status.HTTP_400_BAD_REQUEST
            ) from None
    reader = csv.DictReader(io.StringIO(decoded))
    required = {"通用名", "商品名", "规格", "剂型", "单价", "库存数量", "有效期"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise _error(
            "CSV_HEADER",
            "缺少必填列：通用名、商品名、规格、剂型、单价、库存数量、有效期",
            status.HTTP_400_BAD_REQUEST,
        )
    errors: list[dict[str, int | str]] = []
    valid: list[Drug] = []
    seen: set[tuple[str, str]] = set()
    rows = list(reader)
    for row_number, row in enumerate(rows, start=2):
        try:
            generic_name = (row.get("通用名") or "").strip()
            specification = (row.get("规格") or "").strip()
            dosage_form = (row.get("剂型") or "").strip()
            if not generic_name or not specification or not dosage_form:
                raise ValueError("通用名、规格和剂型不能为空")
            key = (generic_name, specification)
            if key in seen:
                raise ValueError("文件内药品重复")
            seen.add(key)
            unit_price = Decimal((row.get("单价") or "").strip())
            stock_qty = int((row.get("库存数量") or "").strip())
            expiry_raw = (row.get("有效期") or "").strip()
            expiry_date = date.fromisoformat(expiry_raw) if expiry_raw else None
            if unit_price <= 0 or stock_qty < 0:
                raise ValueError("单价必须大于0，库存数量不能为负")
            valid.append(
                Drug(
                    generic_name=generic_name,
                    trade_name=(row.get("商品名") or "").strip() or None,
                    specification=specification,
                    dosage_form=dosage_form,
                    insurance_type=(row.get("医保类别") or "").strip() or None,
                    unit_price=unit_price,
                    stock_qty=stock_qty,
                    expiry_date=expiry_date,
                )
            )
        except (ValueError, ArithmeticError) as exc:
            errors.append({"row": row_number, "reason": str(exc)})
    db.add_all(valid)
    db.flush()
    _audit(
        db,
        user.id,
        "drug.import",
        "drug",
        "batch",
        after={"success": len(valid), "failure": len(errors)},
    )
    db.commit()
    return {"total": len(rows), "success": len(valid), "failure": len(errors), "errors": errors}


def cancel_registration(db: Session, registration_id: int, user: User) -> RegistrationOrder:
    registration = (
        db.query(RegistrationOrder)
        .filter(RegistrationOrder.id == registration_id)
        .with_for_update()
        .first()
    )
    if registration is None:
        raise _error("REGISTRATION_NOT_FOUND", "挂号单不存在", status.HTTP_404_NOT_FOUND)
    if (
        registration.status != RegistrationStatus.PENDING.value
        or registration.prescription is not None
    ):
        raise _error("INVALID_REGISTRATION_STATE", "当前挂号状态不能取消", status.HTTP_409_CONFLICT)
    schedule = (
        db.query(Schedule).filter(Schedule.id == registration.schedule_id).with_for_update().one()
    )
    before = {"status": registration.status, "remain_quota": schedule.remain_quota}
    registration.status = RegistrationStatus.CANCELLED.value
    schedule.remain_quota = min(schedule.total_quota, schedule.remain_quota + 1)
    _audit(
        db,
        user.id,
        "registration.cancel",
        "registration",
        registration.id,
        before,
        {"status": registration.status, "remain_quota": schedule.remain_quota},
    )
    db.commit()
    db.refresh(registration)
    return registration


def today_report(db: Session, report_date: date) -> dict:
    charged_amount = (
        db.query(func.coalesce(func.sum(ChargeOrder.amount), 0))
        .filter(
            func.date(ChargeOrder.paid_at) == report_date.isoformat(),
            ChargeOrder.status == OrderStatus.COMPLETED.value,
        )
        .scalar()
    )
    return {
        "date": report_date,
        "registration_count": db.query(RegistrationOrder)
        .filter(func.date(RegistrationOrder.created_at) == report_date.isoformat())
        .count(),
        "charged_amount": Decimal(str(charged_amount or 0)),
        "dispensed_count": db.query(DispenseOrder)
        .filter(
            func.date(DispenseOrder.dispensed_at) == report_date.isoformat(),
            DispenseOrder.status == OrderStatus.COMPLETED.value,
        )
        .count(),
    }


def create_registration(db: Session, payload: RegistrationCreate, user: User) -> RegistrationOrder:
    schedule = (
        db.query(Schedule).filter(Schedule.id == payload.schedule_id).with_for_update().first()
    )
    if schedule is None:
        raise _error("SCHEDULE_NOT_FOUND", "排班不存在", status.HTTP_404_NOT_FOUND)
    if schedule.status != "active":
        raise _error("SCHEDULE_INACTIVE", "排班不可用", status.HTTP_409_CONFLICT)
    if schedule.remain_quota <= 0:
        raise _error("QUOTA_EXHAUSTED", "号源已满", status.HTTP_409_CONFLICT)
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise _error("PATIENT_NOT_FOUND", "患者不存在", status.HTTP_404_NOT_FOUND)

    next_queue = (
        db.query(func.max(RegistrationOrder.queue_no))
        .filter(RegistrationOrder.schedule_id == schedule.id)
        .scalar()
        or 0
    ) + 1
    schedule.remain_quota -= 1
    registration = RegistrationOrder(
        patient_id=patient.id,
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        queue_no=next_queue,
        status=RegistrationStatus.PENDING.value,
        amount=Decimal("0.00"),
        created_by=user.id,
    )
    db.add(registration)
    db.flush()
    _audit(
        db,
        user.id,
        "registration.create",
        "registration",
        registration.id,
        after={"schedule_id": schedule.id, "queue_no": next_queue, "patient_id": patient.id},
    )
    db.commit()
    db.refresh(registration)
    return registration


def create_prescription(db: Session, payload: PrescriptionCreate, user: User) -> Prescription:
    doctor = user.doctor
    if doctor is None:
        raise _error(
            "DOCTOR_PROFILE_REQUIRED", "当前医生账号未绑定医生档案", status.HTTP_403_FORBIDDEN
        )
    registration = db.get(RegistrationOrder, payload.registration_id)
    if registration is None:
        raise _error("REGISTRATION_NOT_FOUND", "挂号单不存在", status.HTTP_404_NOT_FOUND)
    if registration.doctor_id != doctor.id:
        raise _error(
            "REGISTRATION_FORBIDDEN", "不能为其他医生的挂号开方", status.HTTP_403_FORBIDDEN
        )
    if registration.status == RegistrationStatus.CANCELLED.value:
        raise _error("REGISTRATION_CANCELLED", "已取消挂号不能开方", status.HTTP_409_CONFLICT)
    if registration.prescription is not None:
        raise _error("PRESCRIPTION_EXISTS", "该挂号已有处方", status.HTTP_409_CONFLICT)

    prescription = Prescription(
        registration_id=registration.id,
        doctor_id=doctor.id,
        diagnosis_code=payload.diagnosis_code,
        diagnosis_name=payload.diagnosis_name,
        status=PrescriptionStatus.DRAFT.value,
        total_amount=Decimal("0.00"),
    )
    db.add(prescription)
    db.flush()
    for item in payload.items:
        drug = db.get(Drug, item.drug_id)
        if drug is None or drug.status != "active":
            db.rollback()
            raise _error("DRUG_NOT_FOUND", "药品不存在或已停用", status.HTTP_400_BAD_REQUEST)
        prescription.items.append(
            PrescriptionItem(
                drug_id=drug.id,
                quantity=item.quantity,
                unit_price=drug.unit_price,
                dosage=item.dosage,
                frequency=item.frequency,
                days=item.days,
            )
        )
    _audit(
        db,
        user.id,
        "prescription.create",
        "prescription",
        prescription.id,
        after={"status": prescription.status},
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def submit_prescription(db: Session, prescription_id: int, user: User) -> Prescription:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise _error("PRESCRIPTION_NOT_FOUND", "处方不存在", status.HTTP_404_NOT_FOUND)
    if user.doctor is None or prescription.doctor_id != user.doctor.id:
        raise _error("PRESCRIPTION_FORBIDDEN", "不能提交其他医生的处方", status.HTTP_403_FORBIDDEN)
    if prescription.status != PrescriptionStatus.DRAFT.value:
        raise _error("INVALID_PRESCRIPTION_STATE", "只有草稿处方可以提交", status.HTTP_409_CONFLICT)
    before = {"status": prescription.status}
    prescription.status = PrescriptionStatus.PENDING_CHARGE.value
    _audit(
        db,
        user.id,
        "prescription.submit",
        "prescription",
        prescription.id,
        before,
        {"status": prescription.status},
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def charge_prescription(db: Session, prescription_id: int, user: User) -> ChargeOrder:
    prescription = (
        db.query(Prescription)
        .options(joinedload(Prescription.items))
        .filter(Prescription.id == prescription_id)
        .with_for_update()
        .first()
    )
    if prescription is None:
        raise _error("PRESCRIPTION_NOT_FOUND", "处方不存在", status.HTTP_404_NOT_FOUND)
    if prescription.status != PrescriptionStatus.PENDING_CHARGE.value:
        raise _error("INVALID_PRESCRIPTION_STATE", "处方状态不允许收费", status.HTTP_409_CONFLICT)
    if prescription.charge_order is not None:
        raise _error("CHARGE_EXISTS", "处方已收费，不能重复收费", status.HTTP_409_CONFLICT)

    total = Decimal("0.00")
    drug_updates: list[tuple[Drug, int]] = []
    for item in prescription.items:
        drug = db.query(Drug).filter(Drug.id == item.drug_id).with_for_update().first()
        if drug is None or drug.status != "active":
            db.rollback()
            raise _error("DRUG_NOT_FOUND", "收费药品不存在或已停用", status.HTTP_400_BAD_REQUEST)
        if drug.expiry_date is not None and drug.expiry_date < date.today():
            db.rollback()
            raise _error("DRUG_EXPIRED", "药品已过期", status.HTTP_400_BAD_REQUEST)
        if drug.stock_qty < item.quantity:
            db.rollback()
            raise _error("INSUFFICIENT_STOCK", "药品库存不足", status.HTTP_400_BAD_REQUEST)
        item.unit_price = drug.unit_price
        total += drug.unit_price * item.quantity
        drug_updates.append((drug, item.quantity))

    for drug, quantity in drug_updates:
        drug.stock_qty -= quantity
    before = {
        "status": prescription.status,
        "stock": {str(d.id): d.stock_qty + q for d, q in drug_updates},
    }
    prescription.total_amount = total
    prescription.status = PrescriptionStatus.PAID.value
    charge = ChargeOrder(
        prescription_id=prescription.id,
        amount=total,
        status=OrderStatus.COMPLETED.value,
        paid_at=datetime.now(UTC),
        created_by=user.id,
    )
    db.add(charge)
    db.flush()
    _audit(
        db,
        user.id,
        "prescription.charge",
        "prescription",
        prescription.id,
        before,
        {"status": prescription.status, "amount": str(total)},
    )
    db.commit()
    db.refresh(charge)
    return charge


def dispense_prescription(db: Session, prescription_id: int, user: User) -> DispenseOrder:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise _error("PRESCRIPTION_NOT_FOUND", "处方不存在", status.HTTP_404_NOT_FOUND)
    if prescription.status != PrescriptionStatus.PAID.value:
        raise _error(
            "INVALID_PRESCRIPTION_STATE", "只有已收费处方可以发药", status.HTTP_409_CONFLICT
        )
    if prescription.dispense_order is not None:
        raise _error("DISPENSE_EXISTS", "处方已发药，不能重复发药", status.HTTP_409_CONFLICT)
    before = {"status": prescription.status}
    prescription.status = PrescriptionStatus.DISPENSED.value
    dispense = DispenseOrder(
        prescription_id=prescription.id,
        pharmacist_id=user.id,
        status=OrderStatus.COMPLETED.value,
        dispensed_at=datetime.now(UTC),
    )
    db.add(dispense)
    db.flush()
    _audit(
        db,
        user.id,
        "prescription.dispense",
        "prescription",
        prescription.id,
        before,
        {"status": prescription.status},
    )
    db.commit()
    db.refresh(dispense)
    return dispense
