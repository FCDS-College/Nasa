"""Create the initial provenance, research, and analysis schema."""

from alembic import op

from flame_api.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunk_full_text ON document_chunk USING gin (to_tsvector('english', text))")


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())