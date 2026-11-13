"""nlp_record: source-linked NLP extraction candidates (D1).

0001 builds its schema from the live ORM metadata, so on a fresh database the table already exists; it is
therefore created only if missing. The table is spelled out here so later model changes cannot alter this revision.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_nlp_record"
down_revision = "0009_video_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("nlp_record"):
        return
    op.create_table(
        "nlp_record",
        sa.Column("record_id", sa.String(40), primary_key=True),
        sa.Column("record_type", sa.String(48), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("normalized", sa.Text, nullable=True),
        sa.Column("document_id", sa.String(26), nullable=False),
        sa.Column("document_version", sa.String(32), nullable=False),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("char_start", sa.Integer, nullable=False),
        sa.Column("char_end", sa.Integer, nullable=False),
        sa.Column("chunk_id", sa.String(80), nullable=False),
        sa.Column("extractor", sa.String(64), nullable=False),
        sa.Column("extractor_version", sa.String(96), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="machine_extracted"),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("record_type", "document_id", "chunk_id", "review_status"):
        op.create_index(f"ix_nlp_record_{column}", "nlp_record", [column])
    op.create_index("ix_nlp_record_chunk_extractor", "nlp_record", ["chunk_id", "extractor"])


def downgrade() -> None:
    op.drop_table("nlp_record")
