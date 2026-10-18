from app.db import Base, engine
from app.models import AuditLog  # noqa: F401 - imports all model metadata through package exports


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()
