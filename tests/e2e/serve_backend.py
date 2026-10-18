"""Start a real FastAPI server with isolated, fictional E2E seed data."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path


E2E_DIRECTORY = Path(__file__).resolve().parent
BACKEND_DIRECTORY = E2E_DIRECTORY.parent.parent / "backend"
DATABASE_FILE = E2E_DIRECTORY / "e2e.db"

# Keep the E2E database separate from developer data and remove only this
# generated file before each run, so every flow starts from a known state.
if DATABASE_FILE.exists():
    DATABASE_FILE.unlink()

os.environ["DATABASE_URL"] = "sqlite:///" + str(DATABASE_FILE).replace("\\", "/")
os.environ["JWT_SECRET"] = "e2e-secret-that-is-long-enough"
os.environ["ALLOWED_ORIGINS"] = "http://127.0.0.1:4173"
sys.path.insert(0, str(BACKEND_DIRECTORY))
os.chdir(BACKEND_DIRECTORY)

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Department, Doctor, Drug, Patient, Schedule, User  # noqa: E402
from app.models.entities import UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = User(
            username="admin.demo",
            display_name="演示管理员",
            password_hash=hash_password("Demo123!"),
            role=UserRole.ADMIN.value,
        )
        doctor_user = User(
            username="doctor.demo",
            display_name="演示医生",
            password_hash=hash_password("Demo123!"),
            role=UserRole.DOCTOR.value,
        )
        cashier = User(
            username="cashier.demo",
            display_name="演示收费员",
            password_hash=hash_password("Demo123!"),
            role=UserRole.CASHIER.value,
        )
        pharmacist = User(
            username="pharmacist.demo",
            display_name="演示药师",
            password_hash=hash_password("Demo123!"),
            role=UserRole.PHARMACIST.value,
        )
        db.add_all([admin, doctor_user, cashier, pharmacist])
        db.flush()
        department = Department(code="IM", name="内科")
        db.add(department)
        db.flush()
        doctor = Doctor(
            user_id=doctor_user.id,
            department_id=department.id,
            name="演示医生",
            license_no="E2E-LICENSE-001",
        )
        db.add(doctor)
        db.flush()
        db.add_all(
            [
                Patient(
                    patient_no="P-E2E-001",
                    name="端到端测试患者",
                    id_no_masked="110***********0001",
                    gender="男",
                ),
                Schedule(
                    doctor_id=doctor.id,
                    visit_date=date(2099, 1, 1),
                    period="上午",
                    total_quota=2,
                    remain_quota=2,
                ),
                Drug(
                    generic_name="端到端测试药品",
                    trade_name="E2E药品",
                    specification="10mg*10",
                    dosage_form="片剂",
                    unit_price=Decimal("12.50"),
                    stock_qty=5,
                    expiry_date=date(2099, 12, 31),
                ),
            ]
        )
        db.commit()


if __name__ == "__main__":
    seed()
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )
    )
