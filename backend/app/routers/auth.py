from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, User
from app.schemas.auth import MeResponse, TokenResponse
from app.security import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]
) -> TokenResponse:
    user = db.query(User).filter(User.username == form.username).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.username)
    db.add(
        AuditLog(user_id=user.id, action="login", resource_type="user", resource_id=str(user.id))
    )
    db.commit()
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return MeResponse.model_validate(current_user)
