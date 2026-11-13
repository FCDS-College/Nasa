"""document_chunk.search_tsv_keep: a full-text vector that keeps the words `english` drops (PostgreSQL only; roadmap follow-up to 10).

The `english` configuration treats `he` as a stopword, so helium ("He") is absent from `search_tsv` and from every query. This adds a
text search dictionary (snowball English *without* a stopword list), a configuration `flame_english` that uses it, a stored vector built
with it, and a GIN index. Only `FLAME_LEXICAL_MODE=or_idf` reads it: the AND query keeps using `search_tsv`, because with stopwords
indexed `plainto_tsquery("what is the flame speed")` would require "the" and "is" to match.

Cost: a second tsvector per page and its index (about the size of the first). Derived data; the downgrade removes it.
"""

from alembic import op

revision = "0012_chunk_search_tsv_keep"
down_revision = "0011_chunk_window_embedding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_dict WHERE dictname = 'flame_stem' AND dictnamespace = current_schema()::regnamespace) THEN
                CREATE TEXT SEARCH DICTIONARY flame_stem (TEMPLATE = snowball, Language = english);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'flame_english' AND cfgnamespace = current_schema()::regnamespace) THEN
                CREATE TEXT SEARCH CONFIGURATION flame_english (COPY = english);
                ALTER TEXT SEARCH CONFIGURATION flame_english
                    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart WITH flame_stem;
            END IF;
        END $$
    """)
    op.execute(
        "ALTER TABLE document_chunk ADD COLUMN IF NOT EXISTS search_tsv_keep tsvector "
        "GENERATED ALWAYS AS (to_tsvector('flame_english', text)) STORED"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunk_search_tsv_keep ON document_chunk USING gin (search_tsv_keep)")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_document_chunk_search_tsv_keep")
    op.execute("ALTER TABLE document_chunk DROP COLUMN IF EXISTS search_tsv_keep")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS flame_english")
    op.execute("DROP TEXT SEARCH DICTIONARY IF EXISTS flame_stem")
