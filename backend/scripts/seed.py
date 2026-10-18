from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import Department, Doctor, User
from app.models.entities import UserRole
from app.security import hash_password

DEMO_USERS = (
    ("admin.demo", "演示管理员", UserRole.ADMIN.value),
    ("doctor.demo", "演示医生", UserRole.DOCTOR.value),
    ("cashier.demo", "演示收费员", UserRole.CASHIER.value),
    ("pharmacist.demo", "演示药师", UserRole.PHARMACIST.value),
)


def seed(db: Session) -> None:
    department = db.query(Department).filter(Department.code == "IM").one_or_none()
    if department is None:
        department = Department(code="IM", name="内科")
        db.add(department)
        db.flush()

    users: dict[str, User] = {}
    for username, display_name, role in DEMO_USERS:
        user = db.query(User).filter(User.username == username).one_or_none()
        if user is None:
            user = User(
                username=username,
                display_name=display_name,
                password_hash=hash_password("Demo123!"),
                role=role,
            )
            db.add(user)
            db.flush()
        users[username] = user

    if db.query(Doctor).filter(Doctor.user_id == users["doctor.demo"].id).one_or_none() is None:
        db.add(
            Doctor(
                user_id=users["doctor.demo"].id,
                department_id=department.id,
                name="演示医生",
                license_no="DEMO-LICENSE-001",
            )
        )
    db.commit()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    print("Seed complete. Demo password: Demo123!")


if __name__ == "__main__":
    main()
