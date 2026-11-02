"""experiment.ingested_at: when ingestion wrote the experiment (P2-9).

Search hits used to report the response time for experiments. The backfill takes the latest
non-quarantine ingestion run of the experiment's table file, else the file's retrieved_at. Rows
with neither stay NULL rather than receiving a guessed timestamp.

0001 builds its schema from the live ORM metadata, so on a fresh database the column already
exists by the time this runs; the add is therefore create-if-missing.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_experiment_ingested_at"
down_revision = "0005_api_clients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("experiment")}
    if "ingested_at" not in columns:
        op.add_column("experiment", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE experiment SET ingested_at = COALESCE(
            (SELECT max(r.finished_at) FROM ingestion_run r
              WHERE r.file_id = experiment.table_file_id AND r.transformation_id <> 'quarantine'),
            (SELECT f.retrieved_at FROM file_record f WHERE f.file_id = experiment.table_file_id)
        )
        WHERE ingested_at IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("experiment") as batch:
        batch.drop_column("ingested_at")
