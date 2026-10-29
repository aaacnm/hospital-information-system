from __future__ import annotations

import csv
import io
import json
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, tuple_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AuditLog,
    ChargeOrder,
    DispenseOrder,
    Doctor,
    Drug,
    DrugStock,
    Patient,
    Prescription,
    PrescriptionItem,
    RegistrationOrder,
    Schedule,
    User,
)
from app.models.entities import OrderStatus, PrescriptionStatus, RegistrationStatus
from app.schemas.business import DrugCreate, PatientCreate, PrescriptionCreate, RegistrationCreate
from app.services.rules import business_date, day_bounds, price_total


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
            ip=db.info.get("client_ip"),
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


def list_patients(
    db: Session, keyword: str | None = None, user: User | None = None
) -> list[Patient]:
    query = db.query(Patient)
    if user and user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(
            Patient.registrations.any(RegistrationOrder.doctor_id == user.doctor.id)
        )
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
    if drug.stock_qty:
        db.add(
            DrugStock(
                drug_id=drug.id,
                batch_no="INITIAL",
                quantity=drug.stock_qty,
                expiry_date=drug.expiry_date or date(2099, 12, 31),
            )
        )
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
    valid: list[DrugCreate] = []
    seen: set[tuple[str, str]] = set()
    rows = []
    for row in reader:
        rows.append(row)
        if len(rows) > 5000:
            raise _error("CSV_ROWS", "每次最多导入 5000 行", 400)
    keys = list(
        {((row.get("通用名") or "").strip(), (row.get("规格") or "").strip()) for row in rows}
    )
    existing = set()
    for offset in range(0, len(keys), 200):
        existing.update(
            db.query(Drug.generic_name, Drug.specification)
            .filter(tuple_(Drug.generic_name, Drug.specification).in_(keys[offset : offset + 200]))
            .all()
        )
    total = 0
    for row_number, row in enumerate(rows, start=2):
        total += 1
        try:
            generic_name = (row.get("通用名") or "").strip()
            specification = (row.get("规格") or "").strip()
            dosage_form = (row.get("剂型") or "").strip()
            if not generic_name or not specification or not dosage_form:
                raise ValueError("通用名、规格和剂型不能为空")
            key = (generic_name, specification)
            if key in seen or key in existing:
                raise ValueError("药品名称和规格已存在")
            unit_price = Decimal((row.get("单价") or "").strip())
            stock_qty = int((row.get("库存数量") or "").strip())
            expiry_raw = (row.get("有效期") or "").strip()
            expiry_date = date.fromisoformat(expiry_raw) if expiry_raw else None
            if unit_price <= 0 or stock_qty < 0:
                raise ValueError("单价必须大于0，库存数量不能为负")
            valid.append(
                DrugCreate(
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
            seen.add(key)
        except (ValueError, ArithmeticError, ValidationError) as exc:
            errors.append({"row": row_number, "reason": str(exc)})
    drugs = [Drug(**payload.model_dump()) for payload in valid]
    db.add_all(drugs)
    db.flush()
    db.add_all(
        [
            DrugStock(
                drug_id=drug.id,
                batch_no="IMPORT",
                quantity=drug.stock_qty,
                expiry_date=drug.expiry_date or date(2099, 12, 31),
            )
            for drug in drugs
            if drug.stock_qty
        ]
    )
    _audit(
        db,
        user.id,
        "drug.import",
        "drug",
        "batch",
        after={"success": len(valid), "failure": len(errors)},
    )
    db.commit()
    return {"total": total, "success": len(valid), "failure": len(errors), "errors": errors}


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
    start, end = day_bounds(report_date)
    charged_amount = (
        db.query(func.coalesce(func.sum(ChargeOrder.amount), 0))
        .filter(
            ChargeOrder.paid_at >= start,
            ChargeOrder.paid_at < end,
            ChargeOrder.status == OrderStatus.COMPLETED.value,
        )
        .scalar()
    )
    return {
        "date": report_date,
        "registration_count": db.query(RegistrationOrder)
        .filter(
            RegistrationOrder.created_at >= start,
            RegistrationOrder.created_at < end,
            RegistrationOrder.status != RegistrationStatus.CANCELLED.value,
        )
        .count(),
        "charged_amount": Decimal(str(charged_amount or 0)),
        "dispensed_count": db.query(DispenseOrder)
        .filter(
            DispenseOrder.dispensed_at >= start,
            DispenseOrder.dispensed_at < end,
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
    if schedule.visit_date < business_date():
        raise _error("SCHEDULE_PAST", "不能挂过期排班", status.HTTP_409_CONFLICT)
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
    registration = (
        db.query(RegistrationOrder)
        .filter(RegistrationOrder.id == payload.registration_id)
        .with_for_update(of=RegistrationOrder)
        .first()
    )
    if registration is None:
        raise _error("REGISTRATION_NOT_FOUND", "挂号单不存在", status.HTTP_404_NOT_FOUND)
    if registration.doctor_id != doctor.id:
        raise _error(
            "REGISTRATION_FORBIDDEN", "不能为其他医生的挂号开方", status.HTTP_403_FORBIDDEN
        )
    if registration.status not in {RegistrationStatus.PENDING.value, RegistrationStatus.PAID.value}:
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
    drug_map = {
        drug.id: drug
        for drug in db.query(Drug)
        .filter(Drug.id.in_({item.drug_id for item in payload.items}))
        .all()
    }
    for item in payload.items:
        drug = drug_map.get(item.drug_id)
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
    prescription.total_amount = price_total(
        (item.unit_price, item.quantity) for item in prescription.items
    )
    registration.status = RegistrationStatus.PAID.value
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


def edit_prescription(db: Session, prescription_id: int, payload: PrescriptionCreate, user: User):
    rx = (
        db.query(Prescription)
        .filter_by(id=prescription_id)
        .with_for_update(of=Prescription)
        .first()
    )
    if rx is None:
        raise _error("PRESCRIPTION_NOT_FOUND", "处方不存在", 404)
    if user.doctor is None or user.doctor.id != rx.doctor_id:
        raise _error("FORBIDDEN", "只能编辑本人处方", 403)
    if rx.status != "草稿" or payload.registration_id != rx.registration_id:
        raise _error("INVALID_STATE", "仅能编辑原挂号下的草稿处方", 409)
    drug_map = {
        drug.id: drug
        for drug in db.query(Drug)
        .filter(Drug.id.in_({item.drug_id for item in payload.items}), Drug.status == "active")
        .all()
    }
    if len(drug_map) != len({item.drug_id for item in payload.items}):
        raise _error("DRUG_NOT_FOUND", "存在不可用药品", 400)
    before = {"amount": str(rx.total_amount), "diagnosis": rx.diagnosis_code}
    db.query(PrescriptionItem).filter_by(prescription_id=rx.id).delete(synchronize_session=False)
    db.expire(rx, ["items"])
    rx.items = [
        PrescriptionItem(
            drug_id=item.drug_id,
            quantity=item.quantity,
            unit_price=drug_map[item.drug_id].unit_price,
            dosage=item.dosage,
            frequency=item.frequency,
            days=item.days,
        )
        for item in payload.items
    ]
    rx.diagnosis_code, rx.diagnosis_name = payload.diagnosis_code, payload.diagnosis_name
    rx.total_amount = price_total((item.unit_price, item.quantity) for item in rx.items)
    _audit(
        db,
        user.id,
        "prescription.edit",
        "prescription",
        rx.id,
        before,
        {"amount": str(rx.total_amount)},
    )
    db.commit()
    return rx


def charge_prescription(db: Session, prescription_id: int, user: User) -> ChargeOrder:
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .with_for_update(of=Prescription)
        .first()
    )
    if prescription is None:
        raise _error("PRESCRIPTION_NOT_FOUND", "处方不存在", status.HTTP_404_NOT_FOUND)
    if prescription.status != PrescriptionStatus.PENDING_CHARGE.value:
        raise _error("INVALID_PRESCRIPTION_STATE", "处方状态不允许收费", status.HTTP_409_CONFLICT)
    if prescription.charge_order is not None:
        raise _error("CHARGE_EXISTS", "处方已收费，不能重复收费", status.HTTP_409_CONFLICT)

    quantities = Counter()
    for item in prescription.items:
        quantities[item.drug_id] += item.quantity
    drugs = (
        db.query(Drug)
        .filter(Drug.id.in_(quantities))
        .order_by(Drug.id)
        .with_for_update(of=Drug)
        .all()
    )
    drug_map = {drug.id: drug for drug in drugs}
    stocks = (
        db.query(DrugStock)
        .filter(DrugStock.drug_id.in_(quantities))
        .order_by(DrugStock.expiry_date, DrugStock.id)
        .with_for_update(of=DrugStock)
        .all()
    )
    stock_map: dict[int, list[DrugStock]] = {drug_id: [] for drug_id in quantities}
    for stock in stocks:
        stock_map[stock.drug_id].append(stock)
    allocations = []
    for drug_id, quantity in quantities.items():
        drug = drug_map.get(drug_id)
        if drug is None or drug.status != "active":
            db.rollback()
            raise _error("DRUG_NOT_FOUND", "收费药品不存在或已停用", status.HTTP_400_BAD_REQUEST)
        if not stock_map[drug_id] and drug.stock_qty:
            stock = DrugStock(
                drug_id=drug.id,
                batch_no="LEGACY",
                quantity=drug.stock_qty,
                expiry_date=drug.expiry_date or date(2099, 12, 31),
            )
            db.add(stock)
            stock_map[drug_id].append(stock)
        usable = [stock for stock in stock_map[drug_id] if stock.expiry_date >= business_date()]
        if not usable and drug.stock_qty:
            db.rollback()
            raise _error("DRUG_EXPIRED", "药品已过期", status.HTTP_400_BAD_REQUEST)
        if sum(stock.quantity for stock in usable) < quantity or drug.stock_qty < quantity:
            db.rollback()
            raise _error("INSUFFICIENT_STOCK", "药品库存不足", status.HTTP_400_BAD_REQUEST)
        remaining = quantity
        for stock in usable:
            take = min(remaining, stock.quantity)
            if take:
                allocations.append((stock, take))
                remaining -= take
            if remaining == 0:
                break
    before = {
        "status": prescription.status,
        "stock": {str(drug.id): drug.stock_qty for drug in drugs},
    }
    for stock, quantity in allocations:
        stock.quantity -= quantity
    for drug in drugs:
        drug.stock_qty -= quantities[drug.id]
    # Preserve prescription prices; later price changes affect new prescriptions.
    total = price_total((item.unit_price, item.quantity) for item in prescription.items)
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
        {
            "status": prescription.status,
            "amount": str(total),
            "stock": {str(drug.id): drug.stock_qty for drug in drugs},
            "batches": [
                {"batch": stock.batch_no, "quantity": quantity} for stock, quantity in allocations
            ],
        },
    )
    db.commit()
    db.refresh(charge)
    return charge


def dispense_prescription(db: Session, prescription_id: int, user: User) -> DispenseOrder:
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .with_for_update(of=Prescription)
        .first()
    )
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
    prescription.registration.status = RegistrationStatus.COMPLETED.value
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
