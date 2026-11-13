"""chunk_window_embedding: one vector per window of a page (PostgreSQL + pgvector only; roadmap item 11).

Windows are the unit the dense leg embeds when `FLAME_DENSE_GRANULARITY=window`; a page scores as its best window. The table is
derived data: `python -m flame_api.vector_index build-windows` fills it and re-embeds a page whose text changed.
"""

from alembic import op

revision = "0011_chunk_window_embedding"
down_revision = "0010_nlp_record"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_window_embedding (
            window_id VARCHAR(96) PRIMARY KEY,
            chunk_id VARCHAR(80) NOT NULL REFERENCES document_chunk(chunk_id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            text_sha VARCHAR(16) NOT NULL,
            model TEXT NOT NULL,
            embedding vector(384) NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunk_window_embedding_chunk ON chunk_window_embedding (chunk_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_window_embedding_hnsw ON chunk_window_embedding USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TABLE IF EXISTS chunk_window_embedding")
