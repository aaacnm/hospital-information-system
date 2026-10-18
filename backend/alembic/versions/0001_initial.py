"""Create the initial hospital information system schema."""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Local startup currently creates metadata; this revision anchors future migrations.
    pass


def downgrade() -> None:
    pass
