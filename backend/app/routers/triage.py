from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.provider import TriageProvider, get_triage_provider
from app.db import get_db
from app.models import User
from app.schemas.triage import TriageRequest, TriageResponse
from app.security import get_current_user
from app.services.triage import triage

router = APIRouter(prefix="/api", tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
async def triage_route(
    payload: TriageRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    provider: Annotated[TriageProvider, Depends(get_triage_provider)],
) -> TriageResponse:
    return await triage(db, user, payload.symptoms, provider)
