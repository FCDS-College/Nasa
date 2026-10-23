"""pgvector chunk embeddings and the published index manifest (PostgreSQL only)."""

from alembic import op

revision = "0003_vector_index"
down_revision = "0002_file_size_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_embedding (
            chunk_id VARCHAR(80) PRIMARY KEY REFERENCES document_chunk(chunk_id) ON DELETE CASCADE,
            model TEXT NOT NULL,
            embedding vector(384) NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunk_embedding_hnsw ON chunk_embedding USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_index_manifest (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            row_count INTEGER NOT NULL,
            knowledge_version TEXT NOT NULL,
            built_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TABLE IF EXISTS vector_index_manifest")
    op.execute("DROP TABLE IF EXISTS chunk_embedding")
