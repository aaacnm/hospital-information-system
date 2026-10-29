import csv
import io
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import joinedload

from app.models import (
    ChargeOrder,
    Drug,
    DrugStock,
    Patient,
    Prescription,
    RegistrationOrder,
    Schedule,
    StockMovement,
    User,
)
from app.models.entities import UserRole
from app.routers.workbench import DB, Admin, Current, paginate, prescription_query
from app.schemas.business import (
    ChargeResponse,
    ClinicalRecordInput,
    ClinicalRecordResponse,
    PatientResponse,
    RefundInput,
    RefundResponse,
)
from app.security import require_roles
from app.services.business import _audit, _error
from app.services.clinical_finance import (
    clinical_registration,
    money,
    refund_prescription,
    report_range,
    save_clinical_record,
)
from app.services.diagnoses import DIAGNOSES
from app.services.rules import business_date

router = APIRouter(prefix="/api", tags=["clinical-finance"])
Clinician = Annotated[User, Depends(require_roles(UserRole.DOCTOR, UserRole.ADMIN))]
Writer = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]
Cashier = Annotated[User, Depends(require_roles(UserRole.CASHIER, UserRole.ADMIN))]
Pharmacy = Annotated[User, Depends(require_roles(UserRole.PHARMACIST, UserRole.ADMIN))]


@router.post("/registrations/{registration_id}/start")
def start_consultation(registration_id: int, db: DB, user: Writer):
    row = clinical_registration(db, registration_id, user, write=True)
    if row.status != "候诊":
        raise _error("VISIT_STATE", "只有候诊患者可以开始接诊", 409)
    row.status = "就诊中"
    _audit(db, user.id, "registration.start", "registration", row.id, after={"status": row.status})
    db.commit()
    return {"id": row.id, "status": row.status}


@router.get("/diagnoses")
def diagnoses(user: Current, keyword: str = Query("", max_length=80)):
    needle = keyword.strip().casefold()
    return [
        {"code": code, "name": name, "source": "ICD-10教学示例"}
        for code, name in DIAGNOSES
        if needle in code.casefold() or needle in name
    ][:30]


@router.get("/registrations/{registration_id}/clinical-record")
def clinical_record(registration_id: int, db: DB, user: Clinician):
    row = clinical_registration(db, registration_id, user)
    return {
        "registration_id": row.id,
        "patient": PatientResponse.model_validate(row.patient).model_dump(mode="json"),
        "record": ClinicalRecordResponse.model_validate(row.clinical_record).model_dump(mode="json")
        if row.clinical_record
        else None,
        "locked": bool(row.clinical_record and row.clinical_record.signed_at is not None)
        or row.status in {"已取消", "已完成"}
        or bool(row.prescription and row.prescription.status != "草稿"),
    }


@router.put(
    "/registrations/{registration_id}/clinical-record", response_model=ClinicalRecordResponse
)
def clinical_save(registration_id: int, payload: ClinicalRecordInput, db: DB, user: Writer):
    return save_clinical_record(db, registration_id, payload, user)


@router.get("/patients/{patient_id}/timeline")
def patient_timeline(
    patient_id: int,
    db: DB,
    user: Clinician,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=20),
):
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise _error("PATIENT_NOT_FOUND", "患者不存在", 404)
    query = (
        db.query(RegistrationOrder)
        .filter(RegistrationOrder.patient_id == patient_id)
        .options(
            joinedload(RegistrationOrder.schedule).joinedload(Schedule.doctor),
            joinedload(RegistrationOrder.prescription),
            joinedload(RegistrationOrder.clinical_record),
        )
    )
    if user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(RegistrationOrder.doctor_id == user.doctor.id)
        if not query.first():
            raise _error("FORBIDDEN", "该患者不属于本人的接诊范围", 403)

    def encode(row):
        rx = row.prescription
        note = row.clinical_record
        return {
            "registration_id": row.id,
            "visit_date": row.schedule.visit_date,
            "period": row.schedule.period,
            "doctor_name": row.schedule.doctor.name,
            "status": row.status,
            "prescription_id": rx.id if rx else None,
            "prescription_status": rx.status if rx else None,
            "diagnosis_code": rx.diagnosis_code if rx else None,
            "diagnosis_name": rx.diagnosis_name if rx else None,
            "amount": money(rx.total_amount) if rx else "0.00",
            "chief_complaint": note.chief_complaint if note else None,
            "signed_at": note.signed_at if note else None,
        }

    result = paginate(query.order_by(RegistrationOrder.id.desc()), page, page_size, encode)
    result["patient"] = PatientResponse.model_validate(patient).model_dump(mode="json")
    return result


@router.post("/prescriptions/{prescription_id}/refund", response_model=RefundResponse)
def refund(prescription_id: int, payload: RefundInput, db: DB, user: Cashier):
    return refund_prescription(db, prescription_id, payload.reason, user)


@router.get("/prescriptions/{prescription_id}/receipt")
def receipt(prescription_id: int, db: DB, user: Cashier):
    rx = prescription_query(db, user).filter(Prescription.id == prescription_id).first()
    if rx is None:
        raise _error("NOT_FOUND", "处方不存在或当前不可访问", 404)
    charge = (
        db.query(ChargeOrder)
        .options(joinedload(ChargeOrder.refund))
        .filter_by(prescription_id=rx.id)
        .first()
    )
    if charge is None:
        raise _error("NOT_CHARGED", "处方尚未收费，没有收费凭证", 409)
    operator = db.query(User.display_name).filter(User.id == charge.created_by).scalar()
    return {
        "receipt_no": f"CH-{charge.id:06d}",
        "prescription_no": f"RX-{rx.id:06d}",
        "patient_name": rx.patient_name,
        "patient_no": rx.patient_no,
        "cashier": operator,
        "charge": ChargeResponse.model_validate(charge, from_attributes=True).model_dump(
            mode="json"
        ),
        "refund": RefundResponse.model_validate(charge.refund).model_dump(mode="json")
        if charge.refund
        else None,
    }


@router.get("/billing-records")
def billing_records(
    db: DB,
    user: Cashier,
    status: Literal["completed", "refunded", ""] = "",
    keyword: str = Query("", max_length=80),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        db.query(
            ChargeOrder.id,
            ChargeOrder.prescription_id,
            ChargeOrder.amount,
            ChargeOrder.payment_method,
            ChargeOrder.status,
            Prescription.status.label("prescription_status"),
            ChargeOrder.paid_at,
            Patient.name.label("patient_name"),
            Patient.patient_no,
            User.display_name.label("cashier"),
        )
        .join(Prescription, Prescription.id == ChargeOrder.prescription_id)
        .join(RegistrationOrder, RegistrationOrder.id == Prescription.registration_id)
        .join(Patient, Patient.id == RegistrationOrder.patient_id)
        .join(User, User.id == ChargeOrder.created_by)
    )
    if status:
        query = query.filter(ChargeOrder.status == status)
    if keyword:
        query = query.filter(
            or_(Patient.name.contains(keyword), Patient.patient_no.contains(keyword))
        )

    def encode(row):
        result = dict(row._mapping)
        result["amount"] = money(result["amount"])
        result["receipt_no"] = f"CH-{row.id:06d}"
        return result

    return paginate(query.order_by(ChargeOrder.id.desc()), page, page_size, encode)


@router.get("/stock-movements")
def stock_movements(
    db: DB,
    user: Pharmacy,
    drug_id: int | None = None,
    prescription_id: int | None = None,
    kind: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        db.query(
            StockMovement.id,
            StockMovement.drug_id,
            StockMovement.stock_id,
            StockMovement.prescription_id,
            StockMovement.kind,
            StockMovement.quantity_delta,
            StockMovement.balance_after,
            StockMovement.created_at,
            Drug.generic_name,
            Drug.specification,
            DrugStock.batch_no,
            DrugStock.expiry_date,
            User.display_name.label("operator"),
        )
        .join(Drug, Drug.id == StockMovement.drug_id)
        .join(DrugStock, DrugStock.id == StockMovement.stock_id)
        .outerjoin(User, User.id == StockMovement.created_by)
    )
    if drug_id:
        query = query.filter(StockMovement.drug_id == drug_id)
    if prescription_id:
        query = query.filter(StockMovement.prescription_id == prescription_id)
    if kind:
        query = query.filter(StockMovement.kind == kind)
    return paginate(
        query.order_by(StockMovement.id.desc()), page, page_size, lambda row: dict(row._mapping)
    )


@router.get("/stock-alerts")
def stock_alerts(
    db: DB,
    user: Pharmacy,
    kind: Literal["low", "expiring", "expired", ""] = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    today = business_date()
    horizon = today + timedelta(days=30)
    counts = (
        db.query(
            DrugStock.drug_id,
            func.sum(case((DrugStock.expiry_date >= today, DrugStock.quantity), else_=0)).label(
                "available_stock"
            ),
            func.sum(case((DrugStock.expiry_date < today, DrugStock.quantity), else_=0)).label(
                "expired_quantity"
            ),
            func.sum(
                case(
                    (
                        (DrugStock.expiry_date >= today) & (DrugStock.expiry_date <= horizon),
                        DrugStock.quantity,
                    ),
                    else_=0,
                )
            ).label("expiring_quantity"),
            func.min(
                case(
                    (
                        (DrugStock.quantity > 0) & (DrugStock.expiry_date >= today),
                        DrugStock.expiry_date,
                    ),
                    else_=None,
                )
            ).label("nearest_expiry"),
        )
        .group_by(DrugStock.drug_id)
        .subquery()
    )
    available = func.coalesce(counts.c.available_stock, 0)
    expiring = func.coalesce(counts.c.expiring_quantity, 0)
    expired = func.coalesce(counts.c.expired_quantity, 0)
    query = (
        db.query(
            Drug.id,
            Drug.generic_name,
            Drug.specification,
            Drug.stock_qty,
            available.label("available_stock"),
            expiring.label("expiring_quantity"),
            expired.label("expired_quantity"),
            counts.c.nearest_expiry,
        )
        .outerjoin(counts, counts.c.drug_id == Drug.id)
        .filter(Drug.status == "active")
    )
    query = query.filter(
        available <= 10
        if kind == "low"
        else expiring > 0
        if kind == "expiring"
        else expired > 0
        if kind == "expired"
        else or_(available <= 10, expiring > 0, expired > 0)
    )
    return {
        **paginate(
            query.order_by(available, Drug.id), page, page_size, lambda row: dict(row._mapping)
        ),
        "low_threshold": 10,
        "expiry_days": 30,
    }


@router.get("/reports/range")
def ranged_report(db: DB, user: Admin, start_date: date, end_date: date):
    return report_range(db, start_date, end_date)


@router.post("/reports/range/export")
def export_range(db: DB, user: Admin, start_date: date, end_date: date):
    report = report_range(db, start_date, end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日期", "有效挂号", "收费金额", "退费金额", "净收入", "发药单数"])
    for row in report["days"]:
        writer.writerow(
            [
                row[key]
                for key in [
                    "date",
                    "registration_count",
                    "charged_amount",
                    "refunded_amount",
                    "net_amount",
                    "dispensed_count",
                ]
            ]
        )
    _audit(
        db,
        user.id,
        "report.export",
        "report",
        "range",
        after={"start_date": str(start_date), "end_date": str(end_date)},
    )
    db.commit()
    return {"csv": "\ufeff" + output.getvalue()}
