"""Create generated project reports.

Revision ID: 0007_reports
Revises: 0006_explainability
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_reports"
down_revision = "0006_explainability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_project_id", "reports", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_table("reports")
