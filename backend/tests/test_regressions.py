from datetime import date, timedelta
from decimal import Decimal

from app.ai.provider import get_triage_provider
from app.main import app
from app.models import AuditLog, ChargeOrder, Drug, DrugStock, Prescription, RegistrationOrder, User
from app.services.rules import business_date
from tests.test_business import auth, make_registration, token_for


def pending(client, items):
    registration, cashier = make_registration(client)
    doctor = token_for(client, "doctor.demo")
    rx = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "演示诊断",
            "items": items,
        },
        headers=auth(doctor),
    )
    assert rx.status_code == 201, rx.text
    rx_id = rx.json()["id"]
    assert (
        client.post(f"/api/prescriptions/{rx_id}/submit", headers=auth(doctor)).status_code == 200
    )
    return rx_id, cashier


def test_repeated_drug_cannot_overdraw_stock(client, db):
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 3}, {"drug_id": 1, "quantity": 3}])
    response = client.post(f"/api/prescriptions/{rx}/charge", headers=auth(cashier))
    assert response.status_code == 400
    assert db.get(Drug, 1).stock_qty == 5
    assert db.query(ChargeOrder).count() == 0
    assert db.get(Prescription, rx).status == "待收费"
    assert db.query(AuditLog).filter_by(action="prescription.charge").count() == 0


def test_invoice_is_priced_before_charge_and_keeps_snapshot(client, db):
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 2}])
    assert db.get(Prescription, rx).total_amount == Decimal("25.00")
    admin = token_for(client, "admin.demo")
    assert (
        client.patch(
            "/api/drugs/1/price", json={"unit_price": "20.00"}, headers=auth(admin)
        ).status_code
        == 200
    )
    response = client.post(f"/api/prescriptions/{rx}/charge", headers=auth(cashier))
    assert response.json()["amount"] == "25.00"


def test_batch_fefo_skips_expired_stock(client, db):
    drug = db.get(Drug, 1)
    drug.stock_qty = 8
    db.add_all(
        [
            DrugStock(
                drug_id=1,
                batch_no="expired",
                quantity=3,
                expiry_date=business_date() - timedelta(days=1),
            ),
            DrugStock(
                drug_id=1,
                batch_no="early",
                quantity=2,
                expiry_date=business_date() + timedelta(days=3),
            ),
            DrugStock(drug_id=1, batch_no="late", quantity=3, expiry_date=date(2099, 12, 31)),
        ]
    )
    db.commit()
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 4}])
    assert client.post(f"/api/prescriptions/{rx}/charge", headers=auth(cashier)).status_code == 200
    stock = {s.batch_no: s.quantity for s in db.query(DrugStock).all()}
    assert stock == {"expired": 3, "early": 0, "late": 1}
    pharmacist = token_for(client, "pharmacist.demo")
    assert (
        client.post(f"/api/prescriptions/{rx}/dispense", headers=auth(pharmacist)).status_code
        == 200
    )
    assert db.get(Drug, 1).stock_qty == 4
    assert db.get(RegistrationOrder, 1).status == "已完成"
    assert (
        client.post(f"/api/prescriptions/{rx}/dispense", headers=auth(pharmacist)).status_code
        == 409
    )


def test_csv_repeat_and_bad_then_good_row(client):
    admin = auth(token_for(client, "admin.demo"))
    content = (
        "通用名,商品名,规格,剂型,单价,医保类别,库存数量,有效期\n"
        "新药,演示,10mg,片剂,-1,甲类,2,2099-01-01\n"
        "新药,演示,10mg,片剂,2.00,甲类,2,2099-01-01\n"
    )
    response = client.post(
        "/api/drugs/import",
        files={"file": ("drugs.csv", content.encode(), "text/csv")},
        headers=admin,
    )
    assert response.json()["success"] == 1
    assert response.json()["failure"] == 1
    repeat = client.post(
        "/api/drugs/import",
        files={"file": ("drugs.csv", content.encode(), "text/csv")},
        headers=admin,
    )
    assert repeat.json()["success"] == 0


def test_sensitive_patient_fields_are_masked_and_disabled_login_rejected(client, db):
    cashier = auth(token_for(client, "cashier.demo"))
    patient = client.post(
        "/api/patients",
        json={
            "patient_no": "PRIVATE-1",
            "name": "虚构患者",
            "id_no_masked": "110101200001011234",
            "phone": "13812345678",
        },
        headers=cashier,
    )
    assert patient.json()["id_no_masked"] == "**************1234"
    assert patient.json()["phone"] == "138****5678"
    user = db.query(User).filter_by(username="cashier.demo").one()
    user.status = "disabled"
    db.commit()
    assert (
        client.post(
            "/api/auth/login", data={"username": "cashier.demo", "password": "Demo123!"}
        ).status_code
        == 401
    )
    assert client.get("/api/registrations", headers=cashier).status_code == 401


def test_lists_audit_filters_and_stock_receive(client, db):
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 1}])
    assert (
        client.get("/api/prescriptions?status=待收费", headers=auth(cashier)).json()["items"][0][
            "total_amount"
        ]
        == "12.50"
    )
    pharmacist = auth(token_for(client, "pharmacist.demo"))
    assert client.get(f"/api/prescriptions/{rx}", headers=pharmacist).status_code == 404
    admin = auth(token_for(client, "admin.demo"))
    received = client.post(
        "/api/drugs/1/stocks",
        json={"batch_no": "RECEIVE-1", "quantity": 2, "expiry_date": "2099-12-31"},
        headers=admin,
    )
    assert received.status_code == 201
    assert db.get(Drug, 1).stock_qty == 7
    logs = client.get("/api/audit-logs?action=stock.receive&page_size=1", headers=admin).json()
    assert logs["total"] == 1
    assert logs["items"][0]["action"] == "stock.receive"
    assert client.get("/api/users", headers=auth(cashier)).status_code == 403


def test_private_triage_input_never_reaches_provider(client):
    class Provider:
        calls = 0

        async def complete(self, prompt):
            self.calls += 1
            raise AssertionError("隐私文本不得外发")

    provider = Provider()
    app.dependency_overrides[get_triage_provider] = lambda: provider
    try:
        result = client.post(
            "/api/triage",
            json={"symptoms": "手机号13812345678，发热"},
            headers=auth(token_for(client, "cashier.demo")),
        )
        assert result.json()["source"] == "fallback"
        assert result.json()["urgency"] == "待人工评估"
        assert provider.calls == 0
    finally:
        app.dependency_overrides.pop(get_triage_provider, None)


def test_workbench_directory_lists_schedule_and_export(client):
    admin = auth(token_for(client, "admin.demo"))
    cashier = auth(token_for(client, "cashier.demo"))
    assert client.get("/api/directory", headers=cashier).json()["departments"][0]["name"] == "内科"
    assert client.get("/api/patient-list", headers=cashier).json()["total"] == 1
    assert (
        client.get("/api/drug-list?keyword=测试&page_size=1", headers=cashier).json()["total"] == 2
    )
    assert client.get("/api/registrations", headers=cashier).json()["total"] == 0
    created = client.post(
        "/api/schedules",
        json={"doctor_id": 1, "visit_date": "2099-01-02", "period": "下午", "total_quota": 3},
        headers=admin,
    )
    assert created.status_code == 201
    assert (
        client.post(
            "/api/schedules",
            json={"doctor_id": 1, "visit_date": "2099-01-02", "period": "下午", "total_quota": 3},
            headers=admin,
        ).status_code
        == 409
    )
    assert client.post("/api/reports/today/export", headers=cashier).status_code == 403
    assert "有效挂号量" in client.post("/api/reports/today/export", headers=admin).json()["csv"]
    assert "text/csv" in client.get("/api/import-template").headers["content-type"]
    assert client.get("/api/workload", headers=cashier).json()["pending_count"] == 0


def test_workbench_filters_use_unexpired_stock_and_patient_scope(client, db):
    registration_id, cashier = make_registration(client)
    cashier_headers = auth(cashier)
    doctor = auth(token_for(client, "doctor.demo"))
    db.add_all(
        [
            DrugStock(drug_id=1, batch_no="filter-ok", quantity=3, expiry_date=date(2099, 12, 31)),
            DrugStock(
                drug_id=1,
                batch_no="filter-expired",
                quantity=2,
                expiry_date=business_date() - timedelta(days=1),
            ),
        ]
    )
    db.commit()

    drugs = client.get("/api/drug-list?keyword=测试药品A", headers=cashier_headers).json()
    assert drugs["items"][0]["stock_qty"] == 5
    assert drugs["items"][0]["available_stock"] == 3

    visits = client.get(
        "/api/registrations?visit_date=2099-01-01&status=候诊", headers=cashier_headers
    ).json()
    assert visits["total"] == 1
    assert visits["items"][0]["id"] == registration_id
    assert (
        client.get("/api/registrations?visit_date=2026-01-01", headers=cashier_headers).json()[
            "total"
        ]
        == 0
    )

    rx = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration_id,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "演示诊断",
            "items": [{"drug_id": 1, "quantity": 1}],
        },
        headers=doctor,
    )
    assert rx.status_code == 201, rx.text
    assert client.get("/api/prescriptions?keyword=测试患者", headers=doctor).json()["total"] == 1
    assert (
        client.get("/api/prescriptions?keyword=不存在的患者", headers=doctor).json()["total"] == 0
    )


def test_draft_edit_reprices_and_cannot_edit_after_submission(client):
    registration, cashier = make_registration(client)
    doctor = auth(token_for(client, "doctor.demo"))
    payload = {
        "registration_id": registration,
        "diagnosis_code": "J06.9",
        "diagnosis_name": "演示诊断",
        "items": [{"drug_id": 1, "quantity": 1}],
    }
    rx = client.post("/api/prescriptions", json=payload, headers=doctor).json()["id"]
    payload["items"] = [{"drug_id": 1, "quantity": 2}, {"drug_id": 2, "quantity": 1}]
    edited = client.patch(f"/api/prescriptions/{rx}", json=payload, headers=doctor)
    assert edited.status_code == 200, edited.text
    assert edited.json()["total_amount"] == "28.00"
    assert len(edited.json()["items"]) == 2
    assert (
        client.patch(f"/api/prescriptions/{rx}", json=payload, headers=auth(cashier)).status_code
        == 403
    )
    client.post(f"/api/prescriptions/{rx}/submit", headers=doctor)
    assert client.patch(f"/api/prescriptions/{rx}", json=payload, headers=doctor).status_code == 409


def test_password_change_and_user_status_are_audited(client):
    admin = auth(token_for(client, "admin.demo"))
    users = client.get("/api/users", headers=admin).json()
    cashier = next(user for user in users if user["role"] == "cashier")
    assert (
        client.patch(
            f"/api/users/{cashier['id']}", json={"status": "disabled"}, headers=admin
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", data={"username": cashier["username"], "password": "Demo123!"}
        ).status_code
        == 401
    )
    assert (
        client.patch(
            f"/api/users/{cashier['id']}", json={"status": "active"}, headers=admin
        ).status_code
        == 200
    )
    token = auth(token_for(client, cashier["username"]))
    assert (
        client.post(
            "/api/auth/login", data={"username": cashier["username"], "password": "密" * 25}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/password",
            json={"old_password": "Demo123!", "new_password": "密" * 25},
            headers=token,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/password",
            json={"old_password": "wrong", "new_password": "Another123!"},
            headers=token,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/auth/password",
            json={"old_password": "Demo123!", "new_password": "Another123!"},
            headers=token,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/login", data={"username": cashier["username"], "password": "Another123!"}
        ).status_code
        == 200
    )


def test_unbound_doctor_cannot_read_workbench_data(client, db):
    user = db.query(User).filter_by(username="cashier.demo").one()
    user.role = "doctor"
    db.commit()
    headers = auth(token_for(client, user.username))
    for path in ("/workload", "/patient-list", "/registrations", "/prescriptions"):
        response = client.get("/api" + path, headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "DOCTOR_PROFILE_REQUIRED"
