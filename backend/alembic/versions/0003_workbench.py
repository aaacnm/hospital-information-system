"""Batch inventory, safety constraints and consistent registration states."""
from alembic import op
import sqlalchemy as sa

revision = "0003_workbench"
down_revision = "e2ca1ffdb4c2"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for table, predicate in [("drugs", "stock_qty < 0 OR unit_price <= 0"), ("schedules", "remain_quota < 0 OR remain_quota > total_quota"), ("prescription_items", "quantity <= 0")]:
        if connection.execute(sa.text(f"SELECT COUNT(*) FROM {table} WHERE {predicate}")).scalar():
            raise RuntimeError(f"{table} 已有非法数据；保留备份并人工处理，迁移未覆盖原数据。")
    for table, constraints in [("drugs", [("ck_drug_stock", "stock_qty >= 0"), ("ck_drug_price", "unit_price > 0")]), ("schedules", [("ck_schedule_quota", "remain_quota >= 0 AND remain_quota <= total_quota")]), ("prescription_items", [("ck_item_quantity", "quantity > 0")])]:
        with op.batch_alter_table(table) as batch:
            for name, condition in constraints:
                batch.create_check_constraint(name, condition)
    op.create_table("drug_stocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("batch_no", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_batch_quantity"),
        sa.UniqueConstraint("drug_id", "batch_no", name="uq_drug_batch"))
    op.create_index("ix_drug_stocks_drug_id", "drug_stocks", ["drug_id"])
    op.create_index("ix_drug_stocks_expiry_date", "drug_stocks", ["expiry_date"])
    connection.execute(sa.text("INSERT INTO drug_stocks (drug_id,batch_no,quantity,expiry_date) SELECT id,'LEGACY',stock_qty,COALESCE(expiry_date,'2099-12-31') FROM drugs WHERE stock_qty>0"))
    connection.execute(sa.text("UPDATE registration_orders SET status='候诊' WHERE status='待支付'"))
    connection.execute(sa.text("UPDATE registration_orders SET status='就诊中' WHERE status='已支付'"))
    connection.execute(sa.text("UPDATE registration_orders SET status='就诊中' WHERE status='候诊' AND id IN (SELECT registration_id FROM prescriptions)"))
    connection.execute(sa.text("UPDATE registration_orders SET status='已完成' WHERE id IN (SELECT registration_id FROM prescriptions WHERE status='已发药')"))
    op.create_index("ix_charge_paid_at", "charge_orders", ["paid_at"])
    op.create_index("ix_audit_time_id", "audit_logs", ["created_at", "id"])


def downgrade():
    raise RuntimeError("本迁移保留库存与业务历史；请从迁移前备份恢复，不自动删除批次记录。")
