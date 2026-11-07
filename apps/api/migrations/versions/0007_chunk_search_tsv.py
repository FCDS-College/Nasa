"""document_chunk.search_tsv: a stored tsvector for full-text search (P2-3).

Search filtered on and ranked by `to_tsvector('english', text)`. The GIN index on that expression
answers the match, but the COUNT and `ts_rank_cd` re-parse the text of every matching chunk, which
took about 12 s for a query matching nearly all of 10^5 chunks. A generated column is parsed once
on write and indexed directly; it replaces the expression index from 0001.

PostgreSQL only: other dialects (the SQLite test database) keep substring matching.
"""

from alembic import op

revision = "0007_chunk_search_tsv"
down_revision = "0006_experiment_ingested_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE document_chunk ADD COLUMN IF NOT EXISTS search_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', text)) STORED"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunk_search_tsv ON document_chunk USING gin (search_tsv)")
    op.execute("DROP INDEX IF EXISTS ix_document_chunk_full_text")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunk_full_text ON document_chunk USING gin (to_tsvector('english', text))")
    op.execute("DROP INDEX IF EXISTS ix_document_chunk_search_tsv")
    op.execute("ALTER TABLE document_chunk DROP COLUMN IF EXISTS search_tsv")
