from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


settings = get_settings()
connect_args = (
    {"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_constraints(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_flush")
def record_changes(session, _):
    import json

    from app.models import AuditLog

    user_id = session.info.get("audit_user_id")
    if not user_id:
        return
    for row in list(session.new) + list(session.dirty):
        if isinstance(row, AuditLog) or not session.is_modified(row, include_collections=False):
            continue
        fields = {
            name: str(getattr(row, name))
            for name in (
                "status",
                "stock_qty",
                "quantity",
                "remain_quota",
                "unit_price",
                "total_amount",
            )
            if hasattr(row, name)
        }
        session.add(
            AuditLog(
                user_id=user_id,
                action="entity.write",
                resource_type=row.__tablename__,
                resource_id=str(row.id),
                after_json=json.dumps(fields, ensure_ascii=False),
                ip=session.info.get("client_ip"),
            )
        )


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.info["client_ip"] = request.client.host if request.client else None
        # SQLite has one writer. Acquire its write reservation before authentication reads.
        if (
            db.bind.dialect.name == "sqlite"
            and request.method in {"POST", "PATCH", "PUT", "DELETE"}
            and request.url.path != "/api/triage"
        ):
            db.execute(text("BEGIN IMMEDIATE"))
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
