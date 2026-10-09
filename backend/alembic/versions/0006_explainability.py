"""Persist model explanations with experiment metrics.

Revision ID: 0006_explainability
Revises: 0005_experiments
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_explainability"
down_revision = "0005_experiments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("experiment_metrics", sa.Column("explainability", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("experiment_metrics", "explainability")
