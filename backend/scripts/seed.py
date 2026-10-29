from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Department, Doctor, Drug, DrugStock, Patient, Schedule, User
from app.security import hash_password
from app.services.rules import business_date

DEMO_USERS = (
    ("admin.demo", "演示管理员", "admin"),
    ("doctor.demo", "演示医生", "doctor"),
    ("cashier.demo", "演示收费员", "cashier"),
    ("pharmacist.demo", "演示药师", "pharmacist"),
)


def seed(db: Session) -> None:
    departments = {row.code: row for row in db.query(Department).all()}
    for code, name in [
        ("IM", "内科"),
        ("GP", "全科门诊"),
        ("SUR", "外科"),
        ("GI", "消化内科"),
        ("RESP", "呼吸内科"),
        ("PED", "儿科"),
        ("GYN", "妇产科"),
        ("DERM", "皮肤科"),
    ]:
        if code not in departments:
            departments[code] = Department(code=code, name=name)
            db.add(departments[code])
    users = {row.username: row for row in db.query(User).all()}
    for username, display_name, role in DEMO_USERS:
        if username not in users:
            users[username] = User(
                username=username,
                display_name=display_name,
                password_hash=hash_password("Demo123!"),
                role=role,
            )
            db.add(users[username])
    db.flush()
    doctor = db.query(Doctor).filter_by(user_id=users["doctor.demo"].id).first()
    if doctor is None:
        doctor = Doctor(
            user_id=users["doctor.demo"].id,
            department_id=departments["IM"].id,
            name="演示医生",
            license_no="DEMO-LICENSE-001",
        )
        db.add(doctor)
        db.flush()
    existing = {
        (row.visit_date, row.period)
        for row in db.query(Schedule).filter(Schedule.doctor_id == doctor.id).all()
    }
    for offset in range(7):
        day = business_date() + timedelta(days=offset)
        for period in ("上午", "下午"):
            if (day, period) not in existing:
                db.add(
                    Schedule(
                        doctor_id=doctor.id,
                        visit_date=day,
                        period=period,
                        total_quota=20,
                        remain_quota=20,
                    )
                )
    patient_numbers = {row[0] for row in db.query(Patient.patient_no).all()}
    for i, name in enumerate(["演示患者甲", "演示患者乙", "演示患者丙"], 1):
        number = f"DEMO-{i:03d}"
        if number not in patient_numbers:
            db.add(
                Patient(
                    patient_no=number,
                    name=name,
                    id_no_masked=f"**************{i:04d}",
                    gender="男" if i % 2 else "女",
                    phone="138****0000",
                )
            )
    existing_drugs = {(row.generic_name, row.specification) for row in db.query(Drug).all()}
    for i, (name, specification, price) in enumerate(
        [
            ("演示药品甲", "10mg×10片", "12.50"),
            ("演示药品乙", "5mg×20片", "3.00"),
            ("演示药品丙", "10ml×6支", "8.20"),
        ],
        1,
    ):
        if (name, specification) not in existing_drugs:
            expiry = business_date() + timedelta(days=365)
            drug = Drug(
                generic_name=name,
                trade_name=f"教学样品{i}",
                specification=specification,
                dosage_form="片剂" if i < 3 else "口服液",
                insurance_type="自费（演示）",
                unit_price=Decimal(price),
                stock_qty=100,
                expiry_date=expiry,
            )
            db.add(drug)
            db.flush()
            db.add(
                DrugStock(drug_id=drug.id, batch_no=f"DEMO-{i}", quantity=100, expiry_date=expiry)
            )
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("虚构演示数据初始化完成；重复运行不会清库或补回已消耗的库存。演示密码 Demo123!")


if __name__ == "__main__":
    main()
