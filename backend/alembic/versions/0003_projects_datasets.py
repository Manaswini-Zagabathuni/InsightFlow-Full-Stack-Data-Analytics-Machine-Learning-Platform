"""Create projects, datasets, and dataset columns.

Revision ID: 0003_projects_datasets
Revises: 0002_create_users
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_projects_datasets"
down_revision = "0002_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("row_count", sa.Integer()),
        sa.Column("column_count", sa.Integer()),
        sa.Column("memory_bytes", sa.Integer()),
        sa.Column("missing_cells", sa.Integer()),
        sa.Column("duplicate_rows", sa.Integer()),
        sa.Column("quality_score", sa.Float()),
        sa.Column("quality_issues", sa.JSON()),
        sa.Column("profile_error", sa.String(length=1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])
    op.create_index("ix_datasets_status", "datasets", ["status"])
    op.create_table(
        "dataset_columns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(length=30), nullable=False),
        sa.Column("pandas_dtype", sa.String(length=80), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("missing_percentage", sa.Float(), nullable=False),
        sa.Column("unique_count", sa.Integer(), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_dataset_columns_dataset_id", table_name="dataset_columns")
    op.drop_table("dataset_columns")
    op.drop_index("ix_datasets_status", table_name="datasets")
    op.drop_index("ix_datasets_project_id", table_name="datasets")
    op.drop_table("datasets")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
