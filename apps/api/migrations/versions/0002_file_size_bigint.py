"""Widen file_record.size_bytes: several source archives exceed 2 GiB."""

from alembic import op

revision = "0002_file_size_bigint"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE file_record ALTER COLUMN size_bytes TYPE BIGINT")


def downgrade() -> None:
    op.execute("ALTER TABLE file_record ALTER COLUMN size_bytes TYPE INTEGER")
