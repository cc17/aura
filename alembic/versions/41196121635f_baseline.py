"""baseline — marks existing server schema as the starting point; no DDL changes

Revision ID: 41196121635f
Revises:
Create Date: 2026-05-24 23:12:25.267273

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '41196121635f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Server already has this schema. On first deploy run: uv run alembic stamp head
    pass


def downgrade() -> None:
    pass
