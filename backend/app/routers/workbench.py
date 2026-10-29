import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db import get_db
from app.models import (
    Department,
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
from app.models.entities import UserRole
from app.schemas.business import (
    DrugResponse,
    PatientResponse,
    PrescriptionResponse,
    ScheduleCreate,
    StockCreate,
    StockResponse,
    UserPatch,
)
from app.security import get_current_user, require_roles
from app.services.business import _audit, _error, today_report
from app.services.rules import business_date

router = APIRouter(prefix="/api", tags=["workbench"])
DB = Annotated[Session, Depends(get_db)]
Current = Annotated[User, Depends(get_current_user)]
Admin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def paginate(query, page: int, page_size: int, encode):
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [encode(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/directory")
def directory(db: DB, user: Current):
    departments = (
        db.query(Department.id, Department.name)
        .filter(Department.status == "active")
        .limit(100)
        .all()
    )
    doctors = (
        db.query(Doctor.id, Doctor.name, Doctor.department_id)
        .filter(Doctor.status == "active")
        .limit(100)
        .all()
    )
    return {
        "date": business_date(),
        "departments": [dict(row._mapping) for row in departments],
        "doctors": [dict(row._mapping) for row in doctors],
    }


@router.get("/patient-list")
def patient_list(
    db: DB,
    user: Annotated[
        User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER, UserRole.DOCTOR))
    ],
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Patient)
    if keyword:
        query = query.filter(
            or_(Patient.name.contains(keyword[:80]), Patient.patient_no.contains(keyword[:80]))
        )
    if user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(
            Patient.registrations.any(RegistrationOrder.doctor_id == user.doctor.id)
        )
    return paginate(
        query.order_by(Patient.id.desc()),
        page,
        page_size,
        lambda row: PatientResponse.model_validate(row).model_dump(mode="json"),
    )


@router.get("/drug-list")
def drug_list(
    db: DB,
    user: Current,
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Drug).filter(Drug.status == "active")
    if keyword:
        query = query.filter(
            or_(Drug.generic_name.contains(keyword[:120]), Drug.trade_name.contains(keyword[:120]))
        )
    return paginate(
        query.order_by(Drug.id),
        page,
        page_size,
        lambda row: DrugResponse.model_validate(row).model_dump(mode="json"),
    )


@router.get("/registrations")
def registration_list(
    db: DB,
    user: Current,
    keyword: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        db.query(RegistrationOrder)
        .join(Patient)
        .options(
            joinedload(RegistrationOrder.patient),
            joinedload(RegistrationOrder.schedule).joinedload(Schedule.doctor),
            joinedload(RegistrationOrder.prescription),
        )
    )
    if user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(RegistrationOrder.doctor_id == user.doctor.id)
    elif user.role not in {"admin", "cashier"}:
        raise _error("FORBIDDEN", "当前角色无权查询挂号", 403)
    if keyword:
        query = query.filter(
            or_(Patient.name.contains(keyword[:80]), Patient.patient_no.contains(keyword[:80]))
        )

    def encode(row):
        return {
            "id": row.id,
            "patient_id": row.patient_id,
            "patient_name": row.patient.name,
            "patient_no": row.patient.patient_no,
            "doctor_name": row.schedule.doctor.name,
            "queue_no": row.queue_no,
            "status": row.status,
            "visit_date": row.schedule.visit_date,
            "period": row.schedule.period,
            "prescription_id": row.prescription.id if row.prescription else None,
        }

    return paginate(query.order_by(RegistrationOrder.id.desc()), page, page_size, encode)


def prescription_query(db: Session, user: User):
    query = db.query(Prescription).options(
        selectinload(Prescription.items).joinedload(PrescriptionItem.drug),
        joinedload(Prescription.registration).joinedload(RegistrationOrder.patient),
        joinedload(Prescription.registration)
        .joinedload(RegistrationOrder.schedule)
        .joinedload(Schedule.doctor),
    )
    if user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(Prescription.doctor_id == user.doctor.id)
    if user.role == "pharmacist":
        query = query.filter(Prescription.status.in_(["已收费", "已发药"]))
    if user.role == "cashier":
        query = query.filter(Prescription.status != "草稿")
    return query


@router.get("/prescriptions")
def prescription_list(
    db: DB,
    user: Current,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = prescription_query(db, user)
    if status:
        query = query.filter(Prescription.status == status)
    return paginate(
        query.order_by(Prescription.id.desc()),
        page,
        page_size,
        lambda row: PrescriptionResponse.model_validate(row).model_dump(mode="json"),
    )


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
def prescription_detail(prescription_id: int, db: DB, user: Current):
    row = prescription_query(db, user).filter(Prescription.id == prescription_id).first()
    if row is None:
        raise _error("NOT_FOUND", "处方不存在或不属于当前可访问范围", 404)
    return row


@router.post("/schedules", status_code=201)
def schedule_create(payload: ScheduleCreate, db: DB, user: Admin):
    if payload.visit_date < business_date():
        raise _error("SCHEDULE_PAST", "不能创建过期排班", 400)
    if db.get(Doctor, payload.doctor_id) is None:
        raise _error("DOCTOR_NOT_FOUND", "医生不存在", 404)
    if (
        db.query(Schedule.id)
        .filter_by(
            doctor_id=payload.doctor_id, visit_date=payload.visit_date, period=payload.period
        )
        .first()
    ):
        raise _error("SCHEDULE_EXISTS", "该医生该时段已有排班", 409)
    row = Schedule(**payload.model_dump(), remain_quota=payload.total_quota)
    db.add(row)
    db.flush()
    _audit(db, user.id, "schedule.create", "schedule", row.id)
    db.commit()
    return {"id": row.id, "remain_quota": row.remain_quota}


@router.get("/drugs/{drug_id}/stocks", response_model=list[StockResponse])
def stock_list(drug_id: int, db: DB, user: Current):
    return (
        db.query(DrugStock)
        .filter(DrugStock.drug_id == drug_id)
        .order_by(DrugStock.expiry_date)
        .limit(100)
        .all()
    )


@router.post("/drugs/{drug_id}/stocks", response_model=StockResponse, status_code=201)
def stock_create(
    drug_id: int,
    payload: StockCreate,
    db: DB,
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.PHARMACIST))],
):
    drug = db.query(Drug).filter(Drug.id == drug_id).with_for_update(of=Drug).first()
    if drug is None:
        raise _error("DRUG_NOT_FOUND", "药品不存在", 404)
    if payload.expiry_date < business_date():
        raise _error("EXPIRED", "不能入库过期批次", 400)
    if db.query(DrugStock.id).filter_by(drug_id=drug_id, batch_no=payload.batch_no).first():
        raise _error("BATCH_EXISTS", "批次已存在，请使用新的入库批号", 409)
    row = DrugStock(drug_id=drug_id, **payload.model_dump())
    db.add(row)
    drug.stock_qty += payload.quantity
    db.flush()
    _audit(
        db,
        user.id,
        "stock.receive",
        "drug",
        drug_id,
        after={"batch": payload.batch_no, "quantity": payload.quantity},
    )
    db.commit()
    return row


@router.get("/workload")
def workload(db: DB, user: Current):
    if user.role == "admin":
        return today_report(db, business_date())
    query = db.query(Prescription)
    if user.role == "doctor":
        if user.doctor is None:
            raise _error("DOCTOR_PROFILE_REQUIRED", "未绑定医生", 403)
        query = query.filter(Prescription.doctor_id == user.doctor.id)
        return {
            "date": business_date(),
            "draft_count": query.filter(Prescription.status == "草稿").count(),
            "submitted_count": query.filter(Prescription.status != "草稿").count(),
        }
    target = "待收费" if user.role == "cashier" else "已收费"
    return {
        "date": business_date(),
        "pending_count": query.filter(Prescription.status == target).count(),
    }


@router.get("/import-template")
def import_template():
    return Response(
        "\ufeff通用名,商品名,规格,剂型,单价,医保类别,库存数量,有效期\n导入演示药,教学样品,10mg,片剂,2.50,自费,10,2099-12-31\n",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=drug-template.csv"},
    )


@router.post("/reports/today/export")
def export_report(db: DB, user: Admin):
    report = today_report(db, business_date())
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["日期", "有效挂号量", "收费金额", "发药单数"])
    writer.writerow(
        [
            report["date"],
            report["registration_count"],
            report["charged_amount"],
            report["dispensed_count"],
        ]
    )
    _audit(db, user.id, "report.export", "report", str(report["date"]))
    db.commit()
    return {"csv": stream.getvalue()}


@router.get("/users")
def users(db: DB, user: Admin):
    return [
        dict(row._mapping)
        for row in db.query(User.id, User.username, User.display_name, User.role, User.status)
        .order_by(User.id)
        .limit(100)
        .all()
    ]


@router.patch("/users/{user_id}")
def user_patch(user_id: int, payload: UserPatch, db: DB, user: Admin):
    row = db.get(User, user_id)
    if row is None:
        raise _error("USER_NOT_FOUND", "账号不存在", 404)
    if row.id == user.id:
        raise _error("SELF_DISABLE", "不能禁用当前管理员", 409)
    before = {"status": row.status}
    row.status = payload.status
    _audit(db, user.id, "user.status", "user", row.id, before, {"status": row.status})
    db.commit()
    return {"id": row.id, "status": row.status}
