from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.entities import User, UserRole
from app.security import require_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(
    _: Annotated[User, Depends(require_roles(UserRole.ADMIN))],
) -> dict[str, str]:
    """Minimal RBAC probe used by tests and deployment smoke checks."""
    return {"status": "ok", "scope": "admin"}
