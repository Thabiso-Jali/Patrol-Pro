"""Compatibility marker for the repaired baseline.

Revision ID: 7a28f92acb7e
Revises: aac23d237e98

The original revision attempted to add tenant fields to tables that the
original baseline never created. The repaired baseline now creates the complete
current schema, including organisations and tenant foreign keys. Keeping this
revision ID preserves the existing chain and avoids changing the recorded head
for databases that were already stamped.
"""

from typing import Sequence, Union


revision: str = "7a28f92acb7e"
down_revision: Union[str, Sequence[str], None] = "aac23d237e98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Schema is already present in the repaired baseline."""


def downgrade() -> None:
    """No schema changes are owned by this compatibility marker."""
