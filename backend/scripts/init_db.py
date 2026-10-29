import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    latest_revision = ScriptDirectory.from_config(config).get_current_head()
    url = get_settings().database_url
    legacy_unversioned = False
    if url.startswith("sqlite:///"):
        database = Path(url.removeprefix("sqlite:///"))
        database.parent.mkdir(parents=True, exist_ok=True)
        if database.exists():
            with sqlite3.connect(database) as source:
                revision = source.execute(
                    "SELECT name FROM sqlite_master WHERE name='alembic_version'"
                ).fetchone()
                row = (
                    source.execute("SELECT version_num FROM alembic_version").fetchone()
                    if revision
                    else None
                )
                current = row[0] if row else None
                if current != latest_revision:
                    backup = database.with_suffix(
                        f".backup-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite"
                    )
                    with sqlite3.connect(backup) as destination:
                        source.backup(destination)
                    print(f"迁移前备份：{backup}")
                tables = {
                    row[0]
                    for row in source.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'"
                    )
                }
                if not revision and tables:
                    expected = set(Base.metadata.tables) - {
                        "drug_stocks",
                        "clinical_records",
                        "stock_movements",
                        "refund_orders",
                    }
                    if tables != expected:
                        raise RuntimeError(
                            "无版本数据库结构不匹配原初版，已备份；请人工确认后迁移。"
                        )
                    for table in expected:
                        columns = {
                            row[1] for row in source.execute(f'PRAGMA table_info("{table}")')
                        }
                        expected_columns = set(Base.metadata.tables[table].columns.keys())
                        if table == "charge_orders":
                            expected_columns -= {"payment_method"}
                        if columns != expected_columns:
                            raise RuntimeError(f"{table} 字段不匹配原初版，已备份；停止自动迁移。")
                    legacy_unversioned = True
    if legacy_unversioned:
        command.stamp(config, "e2ca1ffdb4c2")
    command.upgrade(config, "head")
    print("数据库迁移完成。")


if __name__ == "__main__":
    main()
