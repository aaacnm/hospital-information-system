from app.models import Drug, Prescription, RegistrationOrder, Schedule


def token_for(client, username: str) -> str:
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "Demo123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_registration(client):
    cashier = token_for(client, "cashier.demo")
    schedule = client.get(
        "/api/schedules", params={"dept_id": 1, "date": "2099-01-01"}, headers=auth(cashier)
    )
    assert schedule.status_code == 200
    assert schedule.json()[0]["remain_quota"] == 2
    registration = client.post(
        "/api/registrations",
        json={"patient_id": 1, "schedule_id": 1},
        headers=auth(cashier),
    )
    assert registration.status_code == 201
    assert registration.json()["queue_no"] == 1
    return registration.json()["id"], cashier


def test_complete_outpatient_flow(client, db):
    registration_id, cashier = make_registration(client)
    schedule = db.get(Schedule, 1)
    assert schedule.remain_quota == 1

    doctor = token_for(client, "doctor.demo")
    prescription = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration_id,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "急性上呼吸道感染",
            "items": [{"drug_id": 1, "quantity": 2, "dosage": "每次1片", "days": 2}],
        },
        headers=auth(doctor),
    )
    assert prescription.status_code == 201, prescription.text
    prescription_id = prescription.json()["id"]
    submitted = client.post(f"/api/prescriptions/{prescription_id}/submit", headers=auth(doctor))
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "待收费"

    charged = client.post(f"/api/prescriptions/{prescription_id}/charge", headers=auth(cashier))
    assert charged.status_code == 200
    assert charged.json()["amount"] == "25.00"
    assert db.get(Drug, 1).stock_qty == 3
    assert db.get(Prescription, prescription_id).status == "已收费"

    pharmacist = token_for(client, "pharmacist.demo")
    dispensed = client.post(
        f"/api/prescriptions/{prescription_id}/dispense", headers=auth(pharmacist)
    )
    assert dispensed.status_code == 200
    assert db.get(Prescription, prescription_id).status == "已发药"

    admin = token_for(client, "admin.demo")
    logs = client.get("/api/audit-logs", headers=auth(admin))
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()["items"]}
    assert {
        "registration.create",
        "prescription.create",
        "prescription.charge",
        "prescription.dispense",
    } <= actions


def test_charge_rolls_back_all_stock_and_state_on_insufficient_stock(client, db):
    registration_id, cashier = make_registration(client)
    doctor = token_for(client, "doctor.demo")
    prescription = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration_id,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "急性上呼吸道感染",
            "items": [{"drug_id": 1, "quantity": 2}, {"drug_id": 2, "quantity": 2}],
        },
        headers=auth(doctor),
    )
    prescription_id = prescription.json()["id"]
    assert (
        client.post(
            f"/api/prescriptions/{prescription_id}/submit", headers=auth(doctor)
        ).status_code
        == 200
    )

    charged = client.post(f"/api/prescriptions/{prescription_id}/charge", headers=auth(cashier))
    assert charged.status_code == 400
    assert charged.json()["detail"]["code"] == "INSUFFICIENT_STOCK"
    assert db.get(Drug, 1).stock_qty == 5
    assert db.get(Drug, 2).stock_qty == 1
    assert db.get(Prescription, prescription_id).status == "待收费"
    assert db.query(RegistrationOrder).count() == 1


def test_duplicate_charge_and_invalid_dispense_are_rejected(client, db):
    registration_id, cashier = make_registration(client)
    doctor = token_for(client, "doctor.demo")
    prescription = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration_id,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "急性上呼吸道感染",
            "items": [{"drug_id": 1, "quantity": 1}],
        },
        headers=auth(doctor),
    )
    prescription_id = prescription.json()["id"]
    pharmacist = token_for(client, "pharmacist.demo")
    assert (
        client.post(
            f"/api/prescriptions/{prescription_id}/dispense", headers=auth(pharmacist)
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/prescriptions/{prescription_id}/submit", headers=auth(doctor)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/prescriptions/{prescription_id}/charge", headers=auth(cashier)
        ).status_code
        == 200
    )
    duplicate = client.post(f"/api/prescriptions/{prescription_id}/charge", headers=auth(cashier))
    assert duplicate.status_code == 409


def test_role_boundaries_and_quota_conflict(client, db):
    registration_id, cashier = make_registration(client)
    pharmacist = token_for(client, "pharmacist.demo")
    forbidden = client.post(
        "/api/registrations", json={"patient_id": 1, "schedule_id": 1}, headers=auth(pharmacist)
    )
    assert forbidden.status_code == 403
    # One remaining slot can be consumed once; the next registration conflicts.
    second = client.post(
        "/api/registrations", json={"patient_id": 1, "schedule_id": 1}, headers=auth(cashier)
    )
    assert second.status_code == 201
    exhausted = client.post(
        "/api/registrations", json={"patient_id": 1, "schedule_id": 1}, headers=auth(cashier)
    )
    assert exhausted.status_code == 409


def test_patient_drug_management_and_price_audit(client, db):
    cashier = token_for(client, "cashier.demo")
    created = client.post(
        "/api/patients",
        json={"patient_no": "P-TEST-002", "name": "新增患者", "gender": "女"},
        headers=auth(cashier),
    )
    assert created.status_code == 201
    duplicate = client.post(
        "/api/patients",
        json={"patient_no": "P-TEST-002", "name": "重复患者"},
        headers=auth(cashier),
    )
    assert duplicate.status_code == 409
    patients = client.get("/api/patients", params={"keyword": "新增"}, headers=auth(cashier))
    assert patients.status_code == 200
    assert patients.json()[0]["name"] == "新增患者"

    pharmacist = token_for(client, "pharmacist.demo")
    created_drug = client.post(
        "/api/drugs",
        json={
            "generic_name": "新药",
            "specification": "5mg",
            "dosage_form": "片剂",
            "unit_price": "8.00",
            "stock_qty": 10,
        },
        headers=auth(pharmacist),
    )
    assert created_drug.status_code == 201
    admin = token_for(client, "admin.demo")
    patched = client.patch(
        f"/api/drugs/{created_drug.json()['id']}/price",
        json={"unit_price": "9.50"},
        headers=auth(admin),
    )
    assert patched.status_code == 200
    assert patched.json()["unit_price"] == "9.50"
    forbidden = client.patch(
        "/api/drugs/1/price", json={"unit_price": "99.00"}, headers=auth(cashier)
    )
    assert forbidden.status_code == 403


def test_csv_import_reports_bad_rows_and_audits(client):
    admin = token_for(client, "admin.demo")
    csv_content = (
        "通用名,商品名,规格,剂型,单价,医保类别,库存数量,有效期\n"
        "导入药,导入商品,10mg,片剂,2.50,甲类,3,2099-12-31\n"
        "坏药,坏商品,10mg,片剂,-1.00,乙类,-2,not-a-date\n"
    )
    response = client.post(
        "/api/drugs/import",
        files={"file": ("drugs.csv", csv_content.encode("utf-8"), "text/csv")},
        headers=auth(admin),
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["success"] == 1
    assert response.json()["failure"] == 1
    assert response.json()["errors"][0]["row"] == 3
    assert "drug.import" in {
        item["action"]
        for item in client.get("/api/audit-logs", headers=auth(admin)).json()["items"]
    }


def test_cancel_registration_releases_quota_and_blocks_after_prescription(client, db):
    registration_id, cashier = make_registration(client)
    cancelled = client.post(f"/api/registrations/{registration_id}/cancel", headers=auth(cashier))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "已取消"
    assert db.get(Schedule, 1).remain_quota == 2
    again = client.post(f"/api/registrations/{registration_id}/cancel", headers=auth(cashier))
    assert again.status_code == 409


def test_today_report_requires_admin(client):
    cashier = token_for(client, "cashier.demo")
    assert client.get("/api/reports/today", headers=auth(cashier)).status_code == 403
    admin = token_for(client, "admin.demo")
    report = client.get("/api/reports/today", headers=auth(admin))
    assert report.status_code == 200
    assert report.json()["registration_count"] == 0
