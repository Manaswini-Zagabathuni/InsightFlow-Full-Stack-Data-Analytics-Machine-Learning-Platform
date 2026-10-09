"""Create saved visualizations.

Revision ID: 0004_visualizations
Revises: 0003_projects_datasets
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_visualizations"
down_revision = "0003_projects_datasets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visualizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("chart_type", sa.String(length=30), nullable=False),
        sa.Column("x_axis", sa.String(length=255)),
        sa.Column("y_axis", sa.String(length=255)),
        sa.Column("group_column", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visualizations_dataset_id", "visualizations", ["dataset_id"])
    op.create_index("ix_visualizations_project_id", "visualizations", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_visualizations_project_id", table_name="visualizations")
    op.drop_index("ix_visualizations_dataset_id", table_name="visualizations")
    op.drop_table("visualizations")
