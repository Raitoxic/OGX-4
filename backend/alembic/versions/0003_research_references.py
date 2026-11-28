"""VYRO-X research references & citation style columns

Adds full research provenance (used vs. retrieved-but-unused sources) and the
selected citation style to ``tasks``. Additive and backward compatible: existing
rows default to empty lists / ``simple`` and are never rewritten destructively.

Revision ID: 0003_research_references
Revises: 0002_research_attribution
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_research_references"
down_revision: Union[str, None] = "0002_research_attribution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("research_used_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("tasks", sa.Column("research_retrieved_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column(
        "tasks",
        sa.Column("citation_style", sa.String(length=16), nullable=False, server_default="simple"),
    )


def downgrade() -> None:
    op.drop_column("tasks", "citation_style")
    op.drop_column("tasks", "research_retrieved_json")
    op.drop_column("tasks", "research_used_json")