"""Create machine-learning experiments and metrics.

Revision ID: 0005_experiments
Revises: 0004_visualizations
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_experiments"
down_revision = "0004_visualizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("target_column", sa.String(length=255)),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("preprocessing", sa.JSON(), nullable=False),
        sa.Column("selected_models", sa.JSON(), nullable=False),
        sa.Column("model_parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_project_id", "experiments", ["project_id"])
    op.create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])
    op.create_index("ix_experiments_status", "experiments", ["status"])
    op.create_table(
        "experiment_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("hyperparameters", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(length=1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_metrics_experiment_id", "experiment_metrics", ["experiment_id"])


def downgrade() -> None:
    op.drop_index("ix_experiment_metrics_experiment_id", table_name="experiment_metrics")
    op.drop_table("experiment_metrics")
    op.drop_index("ix_experiments_status", table_name="experiments")
    op.drop_index("ix_experiments_dataset_id", table_name="experiments")
    op.drop_index("ix_experiments_project_id", table_name="experiments")
    op.drop_table("experiments")
