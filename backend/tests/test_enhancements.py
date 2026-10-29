from datetime import timedelta

from app.models import Drug
from app.services.rules import business_date
from tests.test_business import auth, make_registration, token_for
from tests.test_regressions import pending

NOTE = {
    "chief_complaint": "虚构演示：咽部不适两天",
    "present_illness": "仅用于课程演示的症状记录",
    "past_history": "未提供既往史，待医生询问",
    "allergy_history": "未确认，开方前须核实",
    "examination": "仅作教学记录，不代表真实检查",
}


def test_clinical_record_permissions_lock_and_history(client):
    registration, cashier = make_registration(client)
    doctor = auth(token_for(client, "doctor.demo"))
    path = f"/api/registrations/{registration}/clinical-record"
    assert client.put(path, json=NOTE, headers=auth(cashier)).status_code == 403
    saved = client.put(path, json=NOTE, headers=doctor)
    assert saved.status_code == 200, saved.text
    assert saved.json()["chief_complaint"] == NOTE["chief_complaint"]
    assert client.get(path, headers=doctor).json()["record"]["signed_at"] is None
    rx = client.post(
        "/api/prescriptions",
        json={
            "registration_id": registration,
            "diagnosis_code": "J06.9",
            "diagnosis_name": "急性上呼吸道感染",
            "items": [{"drug_id": 1, "quantity": 1}],
        },
        headers=doctor,
    ).json()["id"]
    assert client.post(f"/api/prescriptions/{rx}/submit", headers=doctor).status_code == 200
    assert client.get(path, headers=doctor).json()["record"]["signed_at"] is not None
    assert client.put(path, json=NOTE, headers=doctor).status_code == 409
    history = client.get("/api/patients/1/timeline", headers=doctor)
    assert history.status_code == 200
    assert history.json()["items"][0]["prescription_id"] == rx
    assert client.get("/api/patients/1/timeline", headers=auth(cashier)).status_code == 403
    assert client.get("/api/diagnoses?keyword=J06", headers=doctor).json()[0]["code"] == "J06.9"


def test_refund_returns_original_batches_and_preserves_receipts(client, db):
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 2}])
    cashier_headers = auth(cashier)
    paid = client.post(
        f"/api/prescriptions/{rx}/charge",
        json={"payment_method": "银行卡"},
        headers=cashier_headers,
    )
    assert paid.status_code == 200
    assert paid.json()["payment_method"] == "银行卡"
    assert db.get(Drug, 1).stock_qty == 3
    receipt = client.get(f"/api/prescriptions/{rx}/receipt", headers=cashier_headers)
    assert receipt.status_code == 200
    assert receipt.json()["charge"]["amount"] == "25.00"
    refunded = client.post(
        f"/api/prescriptions/{rx}/refund",
        json={"reason": "患者要求取消本次教学处方"},
        headers=cashier_headers,
    )
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["amount"] == "25.00"
    assert db.get(Drug, 1).stock_qty == 5
    assert (
        client.post(
            f"/api/prescriptions/{rx}/refund",
            json={"reason": "重复申请退费"},
            headers=cashier_headers,
        ).status_code
        == 409
    )
    receipt = client.get(f"/api/prescriptions/{rx}/receipt", headers=cashier_headers).json()
    assert receipt["charge"]["status"] == "refunded"
    assert receipt["refund"]["amount"] == "25.00"
    admin = auth(token_for(client, "admin.demo"))
    today = business_date().isoformat()
    report = client.get(f"/api/reports/range?start_date={today}&end_date={today}", headers=admin)
    assert report.status_code == 200
    assert report.json()["totals"]["charged_amount"] == "25.00"
    assert report.json()["totals"]["refunded_amount"] == "25.00"
    assert report.json()["totals"]["net_amount"] == "0.00"
    moves = client.get(f"/api/stock-movements?prescription_id={rx}", headers=admin).json()["items"]
    assert sorted(m["quantity_delta"] for m in moves) == [-2, 2]
    assert len({m["stock_id"] for m in moves}) == 1
    assert (
        client.get("/api/billing-records", headers=cashier_headers).json()["items"][0]["status"]
        == "refunded"
    )


def test_dispensed_refund_and_unauthorized_refund_are_rejected(client):
    rx, cashier = pending(client, [{"drug_id": 1, "quantity": 1}])
    client.post(f"/api/prescriptions/{rx}/charge", headers=auth(cashier))
    pharmacist = auth(token_for(client, "pharmacist.demo"))
    body = {"reason": "测试已发药拒绝退费"}
    assert (
        client.post(f"/api/prescriptions/{rx}/refund", json=body, headers=pharmacist).status_code
        == 403
    )
    assert client.post(f"/api/prescriptions/{rx}/dispense", headers=pharmacist).status_code == 200
    assert (
        client.post(f"/api/prescriptions/{rx}/refund", json=body, headers=auth(cashier)).status_code
        == 409
    )


def test_stock_alerts_and_range_limits(client):
    admin = auth(token_for(client, "admin.demo"))
    soon = (business_date() + timedelta(days=5)).isoformat()
    assert (
        client.post(
            "/api/drugs/1/stocks",
            json={"batch_no": "NEAR-EXPIRY", "quantity": 2, "expiry_date": soon},
            headers=admin,
        ).status_code
        == 201
    )
    alerts = client.get("/api/stock-alerts?kind=expiring", headers=admin)
    assert alerts.status_code == 200
    assert alerts.json()["items"][0]["expiring_quantity"] == 2
    assert client.get("/api/stock-movements?kind=入库", headers=admin).json()["total"] == 1
    assert (
        client.get("/api/stock-alerts", headers=auth(token_for(client, "doctor.demo"))).status_code
        == 403
    )
    assert (
        client.get(
            "/api/reports/range?start_date=2026-10-29&end_date=2026-10-28", headers=admin
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/reports/range?start_date=2026-01-01&end_date=2026-10-29", headers=admin
        ).status_code
        == 400
    )
    export = client.post(
        f"/api/reports/range/export?start_date={business_date()}&end_date={business_date()}",
        headers=admin,
    )
    assert export.status_code == 200
    assert "净收入" in export.json()["csv"]
