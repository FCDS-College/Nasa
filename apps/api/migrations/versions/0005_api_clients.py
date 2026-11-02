"""Per-client API keys (P2-1, ADR-009 step 2).

0001 builds its schema from the live ORM metadata, so on a fresh database `api_client` already
exists by the time this runs. The table is therefore created only if missing. It is spelled out
here rather than taken from the ORM, so later model changes cannot alter this revision.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_api_clients"
down_revision = "0004_phase2_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("api_client"):
        return
    op.create_table(
        "api_client",
        sa.Column("client_id", sa.String(26), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("api_client"):
        op.drop_table("api_client")
