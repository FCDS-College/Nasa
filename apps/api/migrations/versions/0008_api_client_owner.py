"""api_client.owner: the person accountable for a key (ADR-009 step 2).

`admin` became a scope of its own. An admin key must name its owner, so every audited admin action
(actor = client name, never reused) maps to one person. Existing clients keep `owner` NULL and keep
their scopes: a `write` client is not given `admin`, so after this revision it no longer reaches
`/api/admin/*`. Operators create an admin client with `--owner` (docs/operations/SECURITY.md).

0001 builds its schema from the live ORM metadata, so on a fresh database the column already exists;
it is therefore added only if missing.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_api_client_owner"
down_revision = "0007_chunk_search_tsv"
branch_labels = None
depends_on = None


def _has_owner() -> bool:
    return any(column["name"] == "owner" for column in sa.inspect(op.get_bind()).get_columns("api_client"))


def upgrade() -> None:
    if not _has_owner():
        op.add_column("api_client", sa.Column("owner", sa.String(128), nullable=True))


def downgrade() -> None:
    if _has_owner():
        op.drop_column("api_client", "owner")
