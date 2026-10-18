from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.models.entities import UserRole
from app.schemas.business import (
    AuditLogListResponse,
    AuditLogResponse,
    ChargeResponse,
    DispenseResponse,
    DrugCreate,
    DrugImportResponse,
    DrugPricePatch,
    DrugResponse,
    PatientCreate,
    PatientResponse,
    PrescriptionCreate,
    PrescriptionResponse,
    RegistrationCreate,
    RegistrationResponse,
    ReportTodayResponse,
    ScheduleResponse,
)
from app.security import get_current_user, require_roles
from app.services.business import (
    cancel_registration,
    charge_prescription,
    create_drug,
    create_patient,
    create_prescription,
    create_registration,
    dispense_prescription,
    import_drugs,
    list_drugs,
    list_patients,
    list_schedules,
    patch_drug_price,
    submit_prescription,
    today_report,
)

router = APIRouter(prefix="/api", tags=["business"])


@router.get("/schedules", response_model=list[ScheduleResponse])
def schedules(
    db: Annotated[Session, Depends(get_db)],
    visit_date: date = Query(..., alias="date"),  # noqa: B008
    dept_id: int | None = Query(default=None, gt=0),
    _: Annotated[User, Depends(get_current_user)] = None,
) -> list[ScheduleResponse]:
    rows = list_schedules(db, dept_id, visit_date)
    return [
        ScheduleResponse(
            id=row.id,
            doctor_id=row.doctor_id,
            doctor_name=row.doctor.name,
            department_id=row.doctor.department_id,
            department_name=row.doctor.department.name,
            visit_date=row.visit_date,
            period=row.period,
            total_quota=row.total_quota,
            remain_quota=row.remain_quota,
            status=row.status,
        )
        for row in rows
    ]


@router.post(
    "/registrations", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED
)
def registrations(
    payload: RegistrationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER))],
) -> RegistrationResponse:
    return create_registration(db, payload, user)


@router.post("/registrations/{registration_id}/cancel", response_model=RegistrationResponse)
def cancel_registration_route(
    registration_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER))],
) -> RegistrationResponse:
    return cancel_registration(db, registration_id, user)


@router.get("/patients", response_model=list[PatientResponse])
def patients(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.CASHIER))],
    keyword: str | None = Query(default=None, max_length=80),
) -> list[PatientResponse]:
    return list_patients(db, keyword)


@router.post("/patients", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def patient_create(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.CASHIER))
    ],
) -> PatientResponse:
    return create_patient(db, payload, user)


@router.get("/drugs", response_model=list[DrugResponse])
def drugs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    keyword: str | None = Query(default=None, max_length=120),
) -> list[DrugResponse]:
    return list_drugs(db, keyword)


@router.post("/drugs", response_model=DrugResponse, status_code=status.HTTP_201_CREATED)
def drug_create(
    payload: DrugCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.PHARMACIST))],
) -> DrugResponse:
    return create_drug(db, payload, user)


@router.patch("/drugs/{drug_id}/price", response_model=DrugResponse)
def drug_price_patch(
    drug_id: int,
    payload: DrugPricePatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> DrugResponse:
    return patch_drug_price(db, drug_id, payload.unit_price, user)


@router.post("/drugs/import", response_model=DrugImportResponse)
def drug_import(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> DrugImportResponse:
    content = file.file.read()
    if len(content) > 2 * 1024 * 1024:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400, detail={"code": "CSV_TOO_LARGE", "message": "CSV 文件不能超过2MB"}
        )
    return import_drugs(db, content, user)


@router.get("/reports/today", response_model=ReportTodayResponse)
def report_today(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> ReportTodayResponse:
    from datetime import date

    return today_report(db, date.today())


@router.post(
    "/prescriptions", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED
)
def prescriptions(
    payload: PrescriptionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR))],
) -> PrescriptionResponse:
    return create_prescription(db, payload, user)


@router.post("/prescriptions/{prescription_id}/submit", response_model=PrescriptionResponse)
def submit(
    prescription_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR))],
) -> PrescriptionResponse:
    return submit_prescription(db, prescription_id, user)


@router.post("/prescriptions/{prescription_id}/charge", response_model=ChargeResponse)
def charge(
    prescription_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.CASHIER))],
) -> ChargeResponse:
    return charge_prescription(db, prescription_id, user)


@router.post("/prescriptions/{prescription_id}/dispense", response_model=DispenseResponse)
def dispense(
    prescription_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.PHARMACIST))],
) -> DispenseResponse:
    return dispense_prescription(db, prescription_id, user)


@router.get("/audit-logs", response_model=AuditLogListResponse)
def audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> AuditLogListResponse:
    from app.models import AuditLog

    total = db.query(AuditLog).count()
    items = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
