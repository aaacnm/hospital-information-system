"""Create an explicit fictional classroom scenario in a fresh demo database."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from app.db import SessionLocal
from app.models import (
    AuditLog,
    ChargeOrder,
    ClinicalRecord,
    Department,
    DispenseOrder,
    Doctor,
    Drug,
    DrugStock,
    Patient,
    Prescription,
    PrescriptionItem,
    RegistrationOrder,
    Schedule,
    StockMovement,
    User,
)
from app.security import hash_password
from app.services.inventory import record_movement
from app.services.rules import business_date


def seed_showcase(db):
    if db.query(AuditLog.id).filter_by(action="demo.showcase").first():
        return
    if db.query(RegistrationOrder.id).first():
        raise RuntimeError("该数据库已有业务记录；请为展示场景指定新的独立数据库，不覆盖现有业务。")
    today = business_date()
    users = {row.username: row for row in db.query(User).limit(100).all()}
    departments = {row.code: row for row in db.query(Department).limit(100).all()}
    for username, label in [
        ("doctor.resp.demo", "演示呼吸科医生"),
        ("doctor.gi.demo", "演示消化科医生"),
    ]:
        row = User(
            username=username,
            display_name=label,
            role="doctor",
            password_hash=hash_password("Demo123!"),
        )
        users[username] = row
        db.add(row)
    db.flush()
    doctors = [db.query(Doctor).filter_by(user_id=users["doctor.demo"].id).one()]
    for username, code in [("doctor.resp.demo", "RESP"), ("doctor.gi.demo", "GI")]:
        row = Doctor(
            user_id=users[username].id,
            department_id=departments[code].id,
            name=users[username].display_name,
            license_no="TEACHING-" + code,
        )
        doctors.append(row)
        db.add(row)
    patients = db.query(Patient).order_by(Patient.id).limit(30).all()
    for index, label in enumerate(
        [
            "安宁",
            "向晴",
            "知远",
            "星禾",
            "初夏",
            "清和",
            "予安",
            "云舒",
            "景行",
            "南乔",
            "嘉禾",
            "沐言",
        ],
        4,
    ):
        row = Patient(
            patient_no=f"DEMO-{index:03d}",
            name="虚构患者·" + label,
            gender="男" if index % 2 else "女",
            birthday=today.replace(year=today.year - 20 - index),
            phone="139****0000",
            id_no_masked=f"**************{index:04d}",
        )
        patients.append(row)
        db.add(row)
    db.flush()
    schedules = {
        (r.doctor_id, r.visit_date, r.period): r for r in db.query(Schedule).limit(100).all()
    }
    for offset in range(7):
        for doctor in doctors:
            key = (doctor.id, today - timedelta(days=offset), "上午")
            if key not in schedules:
                schedules[key] = Schedule(
                    doctor_id=doctor.id,
                    visit_date=key[1],
                    period="上午",
                    total_quota=30,
                    remain_quota=30,
                )
                db.add(schedules[key])
    new_drugs = []
    for index, (name, specification, price, quantity, days) in enumerate(
        [
            ("对乙酰氨基酚片（教学）", "0.5g×12片", "9.80", 120, 240),
            ("氯雷他定片（教学）", "10mg×6片", "13.20", 160, 300),
            ("蒙脱石散（教学）", "3g×10袋", "18.00", 90, 150),
            ("盐酸氨溴索口服液（教学）", "100ml/瓶", "16.50", 80, 180),
            ("维生素C片（低库存示例）", "0.1g×100片", "4.80", 5, 200),
            ("复方含片（近效期示例）", "12片/盒", "8.00", 24, 10),
            ("教学药品（过期隔离示例）", "10片/盒", "6.00", 7, -5),
        ],
        4,
    ):
        expiry = today + timedelta(days=days)
        drug = Drug(
            generic_name=name,
            trade_name=f"教学样品{index}",
            specification=specification,
            dosage_form="口服液" if "口服液" in name else "散剂" if "散" in name else "片剂",
            insurance_type="自费（教学）",
            unit_price=Decimal(price),
            stock_qty=quantity,
            expiry_date=expiry,
        )
        new_drugs.append(drug)
        db.add(drug)
    db.flush()
    for drug in new_drugs:
        stock = DrugStock(
            drug_id=drug.id,
            batch_no=f"CLASS-{drug.id:03d}",
            quantity=drug.stock_qty,
            expiry_date=drug.expiry_date,
        )
        db.add(stock)
        record_movement(db, stock, stock.quantity, "演示期初", None)
    db.flush()
    medicines = db.query(Drug).order_by(Drug.id).limit(7).all()
    stocks = {
        r.drug_id: r
        for r in db.query(DrugStock).filter(DrugStock.drug_id.in_([d.id for d in medicines])).all()
    }
    cashier = users["cashier.demo"]
    pharmacist = users["pharmacist.demo"]
    movement_rows = []
    case_index = 0

    def encounter(offset, doctor, patient, state):
        nonlocal case_index
        day = today - timedelta(days=offset)
        stamp = datetime.combine(day, time(1 + case_index % 5, case_index % 50), tzinfo=UTC)
        schedule = schedules[(doctor.id, day, "上午")]
        schedule.remain_quota -= 1
        visit = RegistrationOrder(
            patient_id=patient.id,
            doctor_id=doctor.id,
            schedule_id=schedule.id,
            queue_no=schedule.total_quota - schedule.remain_quota,
            status="候诊"
            if state == "候诊"
            else "就诊中"
            if state in {"待收费", "已收费"}
            else "已完成",
            amount=Decimal("0.00"),
            created_by=cashier.id,
            created_at=stamp,
            updated_at=stamp,
        )
        db.add(visit)
        if state == "候诊":
            case_index += 1
            return
        diagnosis = [
            ("J06.9", "急性上呼吸道感染，未特指"),
            ("J20.9", "急性支气管炎，未特指"),
            ("K30", "功能性消化不良"),
        ][doctors.index(doctor)]
        rx = Prescription(
            registration=visit,
            doctor_id=doctor.id,
            diagnosis_code=diagnosis[0],
            diagnosis_name=diagnosis[1],
            status=state,
            total_amount=Decimal("0.00"),
            created_at=stamp,
            updated_at=stamp,
        )
        db.add(rx)
        db.add(
            ClinicalRecord(
                registration=visit,
                doctor_id=doctor.id,
                chief_complaint="虚构教学症状，用于门诊工作台演示",
                present_illness="此记录由课堂场景初始化生成，不对应真实患者。",
                past_history="虚构教学资料，无真实病史。",
                allergy_history="演示资料，实际开方须由医生核对。",
                examination="教学场景未实施实际查体。",
                signed_at=stamp,
                created_at=stamp,
                updated_at=stamp,
            )
        )
        for shift in range(1 + case_index % 2):
            drug = medicines[(case_index + shift) % len(medicines)]
            quantity = 1 + (case_index + shift) % 2
            rx.items.append(
                PrescriptionItem(
                    drug_id=drug.id,
                    quantity=quantity,
                    unit_price=drug.unit_price,
                    dosage="教学示例，须医师核对",
                    frequency="教学示例",
                    days=2,
                )
            )
            rx.total_amount += drug.unit_price * quantity
            if state in {"已收费", "已发药"}:
                stock = stocks[drug.id]
                stock.quantity -= quantity
                drug.stock_qty -= quantity
                movement_rows.append((stock, quantity, stock.quantity, rx, stamp))
        if state in {"已收费", "已发药"}:
            db.add(
                ChargeOrder(
                    prescription=rx,
                    amount=rx.total_amount,
                    status="completed",
                    payment_method=["现金", "银行卡", "模拟扫码"][case_index % 3],
                    created_by=cashier.id,
                    paid_at=stamp + timedelta(minutes=12),
                    created_at=stamp + timedelta(minutes=12),
                )
            )
        if state == "已发药":
            db.add(
                DispenseOrder(
                    prescription=rx,
                    pharmacist_id=pharmacist.id,
                    status="completed",
                    dispensed_at=stamp + timedelta(minutes=18),
                    created_at=stamp + timedelta(minutes=18),
                )
            )
        case_index += 1

    for offset in range(6, 0, -1):
        for doctor in doctors:
            for repeat in range(1 + offset % 3):
                encounter(offset, doctor, patients[(case_index + repeat) % len(patients)], "已发药")
    for index, state in enumerate(
        ["已发药", "待收费", "已收费", "待收费", "候诊", "候诊", "候诊", "候诊"]
    ):
        encounter(
            0,
            doctors[0] if index < 6 else doctors[index - 5],
            patients[index % len(patients)],
            state,
        )
    db.flush()
    for stock, quantity, balance, rx, stamp in movement_rows:
        db.add(
            StockMovement(
                stock=stock,
                drug_id=stock.drug_id,
                prescription_id=rx.id,
                quantity_delta=-quantity,
                balance_after=balance,
                kind="收费出库",
                created_by=cashier.id,
                created_at=stamp + timedelta(minutes=12),
            )
        )
    db.add(
        AuditLog(
            user_id=cashier.id,
            action="demo.showcase",
            resource_type="demo",
            resource_id="classroom",
            after_json='{"source":"虚构教学场景初始化，不是真实业务记录","days":7}',
        )
    )
    db.commit()


def main():
    with SessionLocal() as db:
        seed_showcase(db)
    print(
        "课堂展示场景已准备：三科室、近7日记录、候诊与待办、库存提醒；全部为虚构数据，重复启动不重置业务。"
    )


if __name__ == "__main__":
    main()
