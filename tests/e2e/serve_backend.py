"""Run the ordinary migration and seed in a temporary E2E database."""

import os
from pathlib import Path
import sys
import tempfile

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="his-e2e-") as directory:
        os.environ["DATABASE_URL"] = (
            "sqlite:///" + (Path(directory) / "demo.sqlite").as_posix()
        )
        os.environ["JWT_SECRET"] = "e2e-isolated-secret-not-for-sharing"
        os.environ["ALLOWED_ORIGINS"] = "http://127.0.0.1:4173"
        from scripts.init_db import main as migrate
        from scripts.seed import main as seed

        migrate()
        seed()
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
