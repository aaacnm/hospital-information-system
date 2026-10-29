from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ChargeOrder,
    ClinicalRecord,
    Department,
    DispenseOrder,
    Doctor,
    Drug,
    DrugStock,
    Prescription,
    RefundOrder,
    RegistrationOrder,
    StockMovement,
    User,
)
from app.schemas.business import ClinicalRecordInput
from app.services.business import _audit, _error
from app.services.inventory import record_movement
from app.services.rules import day_bounds


def clinical_registration(db: Session, registration_id: int, user: User, write: bool = False):
    query = db.query(RegistrationOrder).options(
        joinedload(RegistrationOrder.patient),
        joinedload(RegistrationOrder.clinical_record),
        joinedload(RegistrationOrder.prescription),
        joinedload(RegistrationOrder.schedule),
    )
    if write:
        query = query.with_for_update(of=RegistrationOrder)
    row = query.filter(RegistrationOrder.id == registration_id).populate_existing().first()
    if row is None:
        raise _error("REGISTRATION_NOT_FOUND", "挂号不存在", 404)
    if user.role == "doctor" and (user.doctor is None or user.doctor.id != row.doctor_id):
        raise _error("FORBIDDEN", "只能访问本人接诊记录", 403)
    return row


def save_clinical_record(
    db: Session, registration_id: int, payload: ClinicalRecordInput, user: User
):
    row = clinical_registration(db, registration_id, user, write=True)
    if (
        (row.clinical_record and row.clinical_record.signed_at is not None)
        or row.status in {"已取消", "已完成"}
        or (row.prescription and row.prescription.status != "草稿")
    ):
        raise _error("CLINICAL_LOCKED", "本次诊疗记录已锁定，不能修改", 409)
    record = row.clinical_record
    if record is None:
        record = ClinicalRecord(registration=row, doctor_id=row.doctor_id, **payload.model_dump())
        db.add(record)
    else:
        for name, value in payload.model_dump().items():
            setattr(record, name, value)
    db.flush()
    _audit(
        db,
        user.id,
        "clinical.save",
        "clinical_record",
        record.id,
        after={"registration_id": row.id},
    )
    db.commit()
    return record


def refund_prescription(db: Session, prescription_id: int, reason: str, user: User):
    rx = (
        db.query(Prescription)
        .filter_by(id=prescription_id)
        .with_for_update(of=Prescription)
        .first()
    )
    if rx is None:
        raise _error("NOT_FOUND", "处方不存在", 404)
    if rx.status != "已收费":
        raise _error("REFUND_STATE", "仅尚未发药的已收费处方支持全额退费", 409)
    charge = (
        db.query(ChargeOrder).filter_by(prescription_id=rx.id).with_for_update(of=ChargeOrder).one()
    )
    if charge.status != "completed" or charge.refund is not None:
        raise _error("REFUND_EXISTS", "该收费记录不能重复退费", 409)
    movements = db.query(StockMovement).filter_by(prescription_id=rx.id, kind="收费出库").all()
    expected = Counter()
    for item in rx.items:
        expected[item.drug_id] += item.quantity
    recorded = Counter()
    for movement in movements:
        recorded[movement.drug_id] -= movement.quantity_delta
    if not movements or recorded != expected:
        raise _error(
            "REFUND_BATCH_HISTORY",
            "缺少完整批次出库记录，不能自动退费回库；请人工核对历史凭据",
            409,
        )
    drug_map = {
        row.id: row
        for row in db.query(Drug)
        .filter(Drug.id.in_(expected))
        .order_by(Drug.id)
        .with_for_update(of=Drug)
        .all()
    }
    stock_ids = sorted({row.stock_id for row in movements})
    stocks = {}
    for offset in range(0, len(stock_ids), 200):
        stocks.update(
            {
                row.id: row
                for row in db.query(DrugStock)
                .filter(DrugStock.id.in_(stock_ids[offset : offset + 200]))
                .order_by(DrugStock.id)
                .with_for_update(of=DrugStock)
                .all()
            }
        )
    for movement in movements:
        stock = stocks[movement.stock_id]
        quantity = -movement.quantity_delta
        stock.quantity += quantity
        drug_map[movement.drug_id].stock_qty += quantity
        record_movement(db, stock, quantity, "退费回库", user, rx.id)
    refund = RefundOrder(
        charge_id=charge.id,
        prescription_id=rx.id,
        amount=charge.amount,
        reason=reason,
        created_by=user.id,
        refunded_at=datetime.now(UTC),
    )
    db.add(refund)
    charge.status = "refunded"
    rx.status = "已退费"
    rx.registration.status = "已完成"
    db.flush()
    _audit(
        db,
        user.id,
        "prescription.refund",
        "prescription",
        rx.id,
        before={"status": "已收费"},
        after={
            "status": rx.status,
            "amount": str(refund.amount),
            "refund_id": refund.id,
            "batches": [{"stock_id": m.stock_id, "quantity": -m.quantity_delta} for m in movements],
        },
    )
    db.commit()
    return refund


def money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def report_range(db: Session, start_date: date, end_date: date):
    length = (end_date - start_date).days + 1
    if not 1 <= length <= 90:
        raise _error("REPORT_RANGE", "结束日期不能早于开始日期，每次最多查询90天", 400)
    start, _ = day_bounds(start_date)
    _, end = day_bounds(end_date)

    def daily(time, value, *conditions):
        day = func.date(time, "+8 hours")
        return {
            row[0]: row[1]
            for row in db.query(day, value)
            .filter(time >= start, time < end, *conditions)
            .group_by(day)
            .all()
        }

    registered = daily(
        RegistrationOrder.created_at,
        func.count(RegistrationOrder.id),
        RegistrationOrder.status != "已取消",
    )
    charged = daily(
        ChargeOrder.paid_at,
        func.sum(ChargeOrder.amount),
        ChargeOrder.status.in_(["completed", "refunded"]),
    )
    refunded = daily(RefundOrder.refunded_at, func.sum(RefundOrder.amount))
    dispensed = daily(
        DispenseOrder.dispensed_at,
        func.count(DispenseOrder.id),
        DispenseOrder.status == "completed",
    )
    rows = []
    for offset in range(length):
        day = str(start_date + timedelta(days=offset))
        income = Decimal(str(charged.get(day, 0)))
        returned = Decimal(str(refunded.get(day, 0)))
        rows.append(
            {
                "date": day,
                "registration_count": registered.get(day, 0),
                "charged_amount": money(income),
                "refunded_amount": money(returned),
                "net_amount": money(income - returned),
                "dispensed_count": dispensed.get(day, 0),
            }
        )
    registration_depts = dict(
        db.query(Doctor.department_id, func.count(RegistrationOrder.id))
        .join(RegistrationOrder, RegistrationOrder.doctor_id == Doctor.id)
        .filter(
            RegistrationOrder.created_at >= start,
            RegistrationOrder.created_at < end,
            RegistrationOrder.status != "已取消",
        )
        .group_by(Doctor.department_id)
        .all()
    )
    charged_depts = dict(
        db.query(Doctor.department_id, func.sum(ChargeOrder.amount))
        .join(Prescription, Prescription.doctor_id == Doctor.id)
        .join(ChargeOrder, ChargeOrder.prescription_id == Prescription.id)
        .filter(
            ChargeOrder.paid_at >= start,
            ChargeOrder.paid_at < end,
            ChargeOrder.status.in_(["completed", "refunded"]),
        )
        .group_by(Doctor.department_id)
        .all()
    )
    refunded_depts = dict(
        db.query(Doctor.department_id, func.sum(RefundOrder.amount))
        .join(Prescription, Prescription.doctor_id == Doctor.id)
        .join(RefundOrder, RefundOrder.prescription_id == Prescription.id)
        .filter(RefundOrder.refunded_at >= start, RefundOrder.refunded_at < end)
        .group_by(Doctor.department_id)
        .all()
    )
    departments = [
        {
            "name": row.name,
            "registration_count": registration_depts.get(row.id, 0),
            "charged_amount": money(charged_depts.get(row.id, 0)),
            "refunded_amount": money(refunded_depts.get(row.id, 0)),
            "net_amount": money(
                Decimal(str(charged_depts.get(row.id, 0)))
                - Decimal(str(refunded_depts.get(row.id, 0)))
            ),
        }
        for row in db.query(Department.id, Department.name).order_by(Department.id).limit(100).all()
    ]
    totals = {
        key: sum(row[key] for row in rows) for key in ["registration_count", "dispensed_count"]
    }
    totals.update(
        {
            key: money(sum((Decimal(row[key]) for row in rows), Decimal(0)))
            for key in ["charged_amount", "refunded_amount", "net_amount"]
        }
    )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "days": rows,
        "totals": totals,
        "departments": departments,
    }
