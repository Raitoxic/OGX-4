"""VYRO-X replan change tracking

Adds ``replan_change`` to ``execution_steps`` so the UI can highlight added /
modified / removed steps after a replan. Additive and backward compatible.

Revision ID: 0005_replan_change
Revises: 0004_pdf_dataset
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_replan_change"
down_revision: Union[str, None] = "0004_pdf_dataset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_steps",
        sa.Column("replan_change", sa.String(length=16), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("execution_steps", "replan_change")