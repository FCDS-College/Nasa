"""Video job checkpoints and cancellation (ADR-008).

- `analysis_result.cancel_requested_at`: set by `POST /api/analyses/{id}/cancel` while a job runs.
- `video_checkpoint_frame`: the frames a running video job has measured, written one segment at a
  time, so a job re-queued after a crash resumes after the last segment instead of starting over.

0001 builds its schema from the live ORM metadata, so on a fresh database both already exist; each
is therefore created only if missing. The table is spelled out here rather than taken from the ORM,
so later model changes cannot alter this revision.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_video_checkpoints"
down_revision = "0008_api_client_owner"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "cancel_requested_at" not in _columns("analysis_result"):
        op.add_column("analysis_result", sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))
    if not sa.inspect(op.get_bind()).has_table("video_checkpoint_frame"):
        op.create_table(
            "video_checkpoint_frame",
            sa.Column("analysis_id", sa.String(26),
                      sa.ForeignKey("analysis_result.analysis_id", ondelete="CASCADE"), primary_key=True),
            sa.Column("frame_index", sa.Integer(), primary_key=True),
            sa.Column("video_id", sa.String(64), nullable=False),
            sa.Column("job_digest", sa.String(64), nullable=False),
            sa.Column("row", sa.JSON().with_variant(JSONB, "postgresql"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("video_checkpoint_frame"):
        op.drop_table("video_checkpoint_frame")
    if "cancel_requested_at" in _columns("analysis_result"):
        op.drop_column("analysis_result", "cancel_requested_at")
