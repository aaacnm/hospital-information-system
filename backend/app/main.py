from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.business import router as business_router
from app.routers.triage import router as triage_router
from app.routers.workbench import router as workbench_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(business_router)
app.include_router(triage_router)
app.include_router(workbench_router)


@app.get("/health", tags=["system"])
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "hospital-information-system-api"}


if settings.frontend_dist:
    frontend = Path(settings.frontend_dist).resolve()
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def local_web(path: str):
        if path.startswith(("api/", "health")):
            raise HTTPException(404, "接口不存在")
        return FileResponse(frontend / "index.html")
