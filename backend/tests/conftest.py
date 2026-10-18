import os
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_hospital.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough"

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Department, Doctor, Drug, Patient, Schedule, User  # noqa: E402
from app.security import hash_password  # noqa: E402

TEST_ENGINE = create_engine(
    "sqlite:///./test_hospital.db", connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestingSessionLocal()
    admin = User(
        username="admin.demo",
        display_name="演示管理员",
        password_hash=hash_password("Demo123!"),
        role="admin",
    )
    doctor_user = User(
        username="doctor.demo",
        display_name="演示医生",
        password_hash=hash_password("Demo123!"),
        role="doctor",
    )
    cashier = User(
        username="cashier.demo",
        display_name="演示收费员",
        password_hash=hash_password("Demo123!"),
        role="cashier",
    )
    pharmacist = User(
        username="pharmacist.demo",
        display_name="演示药师",
        password_hash=hash_password("Demo123!"),
        role="pharmacist",
    )
    session.add_all([admin, doctor_user, cashier, pharmacist])
    session.flush()
    department = Department(code="IM", name="内科")
    session.add(department)
    session.flush()
    doctor = Doctor(
        user_id=doctor_user.id,
        department_id=department.id,
        name="演示医生",
        license_no="TEST-LICENSE-001",
    )
    session.add(doctor)
    session.flush()
    session.add(
        Patient(
            patient_no="P-TEST-001",
            name="测试患者",
            id_no_masked="110***********1234",
            gender="男",
        )
    )
    session.add(
        Schedule(
            doctor_id=doctor.id,
            visit_date=date(2099, 1, 1),
            period="上午",
            total_quota=2,
            remain_quota=2,
        )
    )
    session.add_all(
        [
            Drug(
                generic_name="测试药品A",
                trade_name="测试A",
                specification="10mg*10",
                dosage_form="片剂",
                unit_price=Decimal("12.50"),
                stock_qty=5,
                expiry_date=date(2099, 12, 31),
            ),
            Drug(
                generic_name="测试药品B",
                trade_name="测试B",
                specification="20mg*10",
                dosage_form="片剂",
                unit_price=Decimal("3.00"),
                stock_qty=1,
                expiry_date=date(2099, 12, 31),
            ),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
