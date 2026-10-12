"""Phase 2 M8 tables, file quarantine columns and the knowledge-version publication log.

0001 builds its schema from the live ORM metadata, so on a fresh database these tables already
exist by the time this runs. Everything here is therefore create-if-missing.
"""

import sqlalchemy as sa
from alembic import op

from flame_api.models import Base

revision = "0004_phase2_tables"
down_revision = "0003_vector_index"
branch_labels = None
depends_on = None

NEW_TABLES = (
    "knowledge_entity",
    "knowledge_relation",
    "memory",
    "cache_entry",
    "model",
    "dataset",
    "image_asset",
    "audit_event",
    "knowledge_publication",
)


def upgrade() -> None:
    bind = op.get_bind()
    file_columns = {column["name"] for column in sa.inspect(bind).get_columns("file_record")}
    if "status" not in file_columns:
        op.add_column("file_record", sa.Column("status", sa.String(16), nullable=False, server_default="active"))
        op.create_index("ix_file_record_status", "file_record", ["status"])
    if "quarantine_reason" not in file_columns:
        op.add_column("file_record", sa.Column("quarantine_reason", sa.Text(), nullable=True))
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[name] for name in NEW_TABLES], checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables[name] for name in reversed(NEW_TABLES)], checkfirst=True)
    with op.batch_alter_table("file_record") as batch:
        batch.drop_index("ix_file_record_status")
        batch.drop_column("quarantine_reason")
        batch.drop_column("status")
