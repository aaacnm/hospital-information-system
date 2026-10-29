from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, User
from app.schemas.auth import MeResponse, TokenResponse
from app.schemas.business import PasswordChange
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]
) -> TokenResponse:
    user = db.query(User).filter(User.username == form.username).first()
    if (
        user is None
        or user.status != "active"
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.username)
    db.info["audit_user_id"] = user.id
    db.add(
        AuditLog(
            user_id=user.id,
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            ip=db.info.get("client_ip"),
        )
    )
    db.commit()
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse.model_validate(current_user)


@router.post("/password")
def change_password(
    payload: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(400, detail={"code": "WRONG_PASSWORD", "message": "当前密码不正确"})
    current_user.password_hash = hash_password(payload.new_password)
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="user.password",
            resource_type="user",
            resource_id=str(current_user.id),
            ip=db.info.get("client_ip"),
        )
    )
    db.commit()
    return {"message": "密码已更新"}
