"""Initial empty migration placeholder.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add initial tables here when introducing ORM models.
    pass


def downgrade() -> None:
    # Drop initial tables here when introducing ORM models.
    pass
