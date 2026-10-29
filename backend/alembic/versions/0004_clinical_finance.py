"""Clinical notes, payment methods, refunds and a batch movement ledger."""

from alembic import op
import sqlalchemy as sa

revision = "0004_clinical_finance"
down_revision = "0003_workbench"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.add_column("charge_orders", sa.Column("payment_method", sa.String(20), server_default="未记录", nullable=False))
    op.create_table("clinical_records", *timestamps(),
        sa.Column("registration_id", sa.Integer(), sa.ForeignKey("registration_orders.id"), nullable=False, unique=True),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("chief_complaint", sa.String(300), nullable=False),
        sa.Column("present_illness", sa.Text(), nullable=False),
        sa.Column("past_history", sa.Text(), nullable=False),
        sa.Column("allergy_history", sa.Text(), nullable=False),
        sa.Column("examination", sa.Text(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_clinical_records_doctor_id", "clinical_records", ["doctor_id"])
    op.create_table("refund_orders", *timestamps(),
        sa.Column("charge_id", sa.Integer(), sa.ForeignKey("charge_orders.id"), nullable=False, unique=True),
        sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_refund_time", "refund_orders", ["refunded_at"])
    op.create_table("stock_movements", *timestamps(),
        sa.Column("drug_id", sa.Integer(), sa.ForeignKey("drugs.id"), nullable=False),
        sa.Column("stock_id", sa.Integer(), sa.ForeignKey("drug_stocks.id"), nullable=False),
        sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("prescription_id", "stock_id", "kind", name="uq_movement_prescription_batch_kind"),
        sa.CheckConstraint("quantity_delta != 0", name="ck_movement_nonzero"),
        sa.CheckConstraint("balance_after >= 0", name="ck_movement_balance"))
    op.create_index("ix_stock_movements_stock_id", "stock_movements", ["stock_id"])
    op.create_index("ix_stock_movements_prescription_id", "stock_movements", ["prescription_id"])
    op.create_index("ix_movement_drug_time", "stock_movements", ["drug_id", "created_at", "id"])
    op.execute(sa.text("INSERT INTO stock_movements (drug_id,stock_id,kind,quantity_delta,balance_after) SELECT drug_id,id,'迁移期初',quantity,quantity FROM drug_stocks WHERE quantity>0"))


def downgrade():
    raise RuntimeError("本迁移包含诊疗、退费与库存追溯记录；请从迁移前备份恢复，不自动丢弃历史。")
