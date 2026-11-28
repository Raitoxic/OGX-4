"""VYRO-X research attribution columns

Adds per-task research state to ``tasks`` (additive, backward compatible).

Revision ID: 0002_research_attribution
Revises: 0001_vyrox_initial
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_research_attribution"
down_revision: Union[str, None] = "0001_vyrox_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("research_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("research_status", sa.String(length=32), nullable=False, server_default="disabled"))
    op.add_column("tasks", sa.Column("research_duration_ms", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("research_used_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("research_retrieved_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("tasks", "research_retrieved_count")
    op.drop_column("tasks", "research_used_count")
    op.drop_column("tasks", "research_duration_ms")
    op.drop_column("tasks", "research_status")
    op.drop_column("tasks", "research_enabled")