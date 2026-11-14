"""chunk_embedding.text_sha: the hash of the page text each vector was built from (PostgreSQL only; KB audit 2026-11-13).

`vector_index.build_index` embedded only pages without a vector, so a page whose text changed under the same chunk ID (a
normaliser or OCR change) kept its old vector, and the index version `<model>-<rows>-<date>` did not change either. With the
hash, a build re-embeds every page whose text differs and names the index by its content.

Existing rows get NULL: nothing records which text they were built from, so the next build re-embeds them once. Derived
data; the downgrade removes the column.
"""

from alembic import op

revision = "0013_chunk_embedding_text_sha"
down_revision = "0012_chunk_search_tsv_keep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE chunk_embedding ADD COLUMN IF NOT EXISTS text_sha VARCHAR(16)")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE chunk_embedding DROP COLUMN IF EXISTS text_sha")
