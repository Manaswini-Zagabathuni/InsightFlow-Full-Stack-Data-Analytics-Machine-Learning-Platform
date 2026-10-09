"""Phase 1 database baseline.

Revision ID: 0001_initial
Revises: None
"""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Reserve the first revision; domain tables arrive in later phases."""
    pass


def downgrade() -> None:
    pass
