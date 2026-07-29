"""Canonicalise the legacy admin role.

Revision ID: d91f42b78ac0
Revises: c3e74a9d52f1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d91f42b78ac0"
down_revision: Union[str, Sequence[str], None] = "c3e74a9d52f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'role_migrated_from_admin',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(sa.text(
        "UPDATE users SET role = 'administrator', role_migrated_from_admin = true "
        "WHERE role = 'admin'"
    ))
    op.alter_column('users', 'role_migrated_from_admin', server_default=None)


def downgrade() -> None:
    op.execute(sa.text(
        "UPDATE users SET role = 'admin' WHERE role_migrated_from_admin = true"
    ))
    op.drop_column('users', 'role_migrated_from_admin')
