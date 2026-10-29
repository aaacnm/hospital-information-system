from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db as database
from app.db import Base
from app.main import app
from app.models import (
    ChargeOrder,
    Drug,
    DrugStock,
    Patient,
    Prescription,
    RegistrationOrder,
    Schedule,
    User,
)
from app.schemas.business import PrescriptionCreate, RegistrationCreate
from app.security import create_access_token
from app.services.business import create_prescription, create_registration, submit_prescription
from scripts.seed import seed


@pytest.mark.parametrize("scenario", ["last_quota", "last_stock", "same_invoice"])
def test_independent_sqlite_requests_are_atomic(tmp_path, monkeypatch, scenario):
    engine = create_engine(
        "sqlite:///" + str(tmp_path / "concurrent.sqlite"),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(database, "SessionLocal", factory)
    with factory() as db:
        seed(db)
        cashier = db.query(User).filter_by(username="cashier.demo").one()
        doctor = db.query(User).filter_by(username="doctor.demo").one()
        patient = db.query(Patient).first()
        schedule = db.query(Schedule).first()
        token = create_access_token(cashier.username)
        if scenario == "last_quota":
            schedule.total_quota = schedule.remain_quota = 1
            db.commit()
            paths = ["/api/registrations"] * 2
            bodies = [{"patient_id": patient.id, "schedule_id": schedule.id}] * 2
        else:
            drug = db.query(Drug).first()
            drug.stock_qty = 1
            db.query(DrugStock).filter_by(drug_id=drug.id).update({"quantity": 1})
            db.commit()
            ids = []
            for _ in range(1 if scenario == "same_invoice" else 2):
                registration = create_registration(
                    db, RegistrationCreate(patient_id=patient.id, schedule_id=schedule.id), cashier
                )
                rx = create_prescription(
                    db,
                    PrescriptionCreate(
                        registration_id=registration.id,
                        diagnosis_code="J06.9",
                        diagnosis_name="并发演示",
                        items=[{"drug_id": drug.id, "quantity": 1}],
                    ),
                    doctor,
                )
                submit_prescription(db, rx.id, doctor)
                ids.append(rx.id)
            if len(ids) == 1:
                ids *= 2
            paths = [f"/api/prescriptions/{rx}/charge" for rx in ids]
            bodies = [None, None]

    def request(index):
        with TestClient(app) as client:
            return client.post(
                paths[index], json=bodies[index], headers={"Authorization": "Bearer " + token}
            ).status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(request, range(2)))
        assert sum(code in {200, 201} for code in statuses) == 1, statuses
        assert all(code in {200, 201, 400, 409} for code in statuses), statuses
        with factory() as db:
            if scenario == "last_quota":
                assert db.query(RegistrationOrder).count() == 1
                assert db.query(Schedule).first().remain_quota == 0
            else:
                assert db.query(ChargeOrder).count() == 1
                assert db.query(Drug).first().stock_qty == 0
                assert db.query(Prescription).filter_by(status="已收费").count() == 1
    finally:
        engine.dispose()
