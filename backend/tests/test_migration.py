import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def test_migration_and_seed_are_repeatable_and_preserve_existing_data(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "migration.sqlite"
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + database.as_posix(),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for module in ("scripts.init_db", "scripts.seed", "scripts.init_db", "scripts.seed"):
        run = subprocess.run(
            [sys.executable, "-m", module], cwd=root, env=env, capture_output=True, text=True
        )
        assert run.returncode == 0, run.stderr
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 14
        assert db.execute("SELECT COUNT(*) FROM drug_stocks").fetchone()[0] == 3
        db.execute("UPDATE drugs SET stock_qty=99 WHERE id=1")
        db.execute("UPDATE drug_stocks SET quantity=99 WHERE drug_id=1")
    run = subprocess.run(
        [sys.executable, "-m", "scripts.seed"], cwd=root, env=env, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT stock_qty FROM drugs WHERE id=1").fetchone()[0] == 99
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("unversioned", [False, True])
def test_legacy_migration_preserves_business_records_and_makes_backup(tmp_path, unversioned):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "legacy.sqlite"
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + database.as_posix(),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    run = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "e2ca1ffdb4c2"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    with sqlite3.connect(database) as db:
        db.executescript("""
            INSERT INTO users (id,username,display_name,password_hash,role,status)
                VALUES (1,'legacy.doctor','历史演示医生','unused-test-hash','doctor','active');
            INSERT INTO departments (id,code,name,status) VALUES (1,'L','历史演示科室','active');
            INSERT INTO doctors (id,user_id,department_id,name,license_no,status)
                VALUES (1,1,1,'历史演示医生','LEGACY-TEST','active');
            INSERT INTO patients (id,patient_no,name) VALUES (1,'L-001','历史演示患者');
            INSERT INTO drugs
                (id,generic_name,specification,dosage_form,unit_price,stock_qty,expiry_date,status)
                VALUES (1,'历史演示药','10mg','片剂',10,7,'2099-12-31','active');
            INSERT INTO schedules
                (id,doctor_id,visit_date,period,total_quota,remain_quota,status)
                VALUES (1,1,'2099-01-01','上午',20,19,'active');
            INSERT INTO registration_orders
                (id,patient_id,doctor_id,schedule_id,queue_no,status,amount,created_by)
                VALUES (1,1,1,1,1,'已支付',0,1);
            INSERT INTO prescriptions
                (id,registration_id,doctor_id,status,total_amount) VALUES (1,1,1,'已发药',20);
            INSERT INTO prescription_items
                (id,prescription_id,drug_id,quantity,unit_price) VALUES (1,1,1,2,10);
            INSERT INTO charge_orders
                (id,prescription_id,amount,status,created_by) VALUES (1,1,20,'已支付',1);
            INSERT INTO dispense_orders
                (id,prescription_id,pharmacist_id,status) VALUES (1,1,1,'已发药');
        """)
        if unversioned:
            db.execute("DROP TABLE alembic_version")
    run = subprocess.run(
        [sys.executable, "-m", "scripts.init_db"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    backups = list(tmp_path.glob("legacy.backup-*.sqlite"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT stock_qty FROM drugs WHERE id=1").fetchone()[0] == 7
        assert backup.execute("SELECT status FROM registration_orders").fetchone()[0] == "已支付"
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT quantity,batch_no FROM drug_stocks").fetchone() == (7, "LEGACY")
        assert db.execute("SELECT remain_quota FROM schedules").fetchone()[0] == 19
        assert db.execute("SELECT status FROM registration_orders").fetchone()[0] == "已完成"
        assert db.execute("SELECT quantity,unit_price FROM prescription_items").fetchone() == (
            2,
            10,
        )
        assert db.execute("SELECT amount FROM charge_orders").fetchone()[0] == 20
        assert db.execute("SELECT COUNT(*) FROM dispense_orders").fetchone()[0] == 1
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
