"""Add teams and structured patrol assignments.

Revision ID: e42b7f1a9c30
Revises: d91f42b78ac0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e42b7f1a9c30'
down_revision: Union[str, Sequence[str], None] = 'd91f42b78ac0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('staff_identifier', sa.String(), nullable=True))
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text(
            "UPDATE users SET staff_identifier = 'PP-' || LPAD(id::text, 5, '0')"
        ))
    else:
        users = sa.table(
            'users',
            sa.column('id', sa.Integer()),
            sa.column('staff_identifier', sa.String()),
        )
        for user_id in bind.execute(sa.select(users.c.id)).scalars():
            bind.execute(
                users.update()
                .where(users.c.id == user_id)
                .values(staff_identifier=f'PP-{user_id:05d}')
            )
    op.alter_column('users', 'staff_identifier', existing_type=sa.String(), nullable=False)
    op.create_index('ix_users_staff_identifier', 'users', ['staff_identifier'])
    op.create_unique_constraint(
        'uq_users_org_staff_identifier',
        'users',
        ['organisation_id', 'staff_identifier'],
    )

    op.add_column(
        'patrols',
        sa.Column('required_officers', sa.Integer(), nullable=False, server_default='1'),
    )
    op.alter_column('patrols', 'required_officers', server_default=None)

    op.add_column(
        'alerts',
        sa.Column('category', sa.String(), nullable=False, server_default='security'),
    )
    op.add_column('alerts', sa.Column('location', sa.String(), nullable=True))
    op.add_column('alerts', sa.Column('resolution_notes', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('reported_by', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_alerts_reported_by_users', 'alerts', 'users', ['reported_by'], ['id'])
    op.create_index('ix_alerts_category', 'alerts', ['category'])
    op.create_index('ix_alerts_reported_by', 'alerts', ['reported_by'])
    op.alter_column('alerts', 'category', server_default=None)
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text(
            "WITH ranked AS ("
            " SELECT id, ROW_NUMBER() OVER ("
            "  PARTITION BY organisation_id, code ORDER BY id"
            " ) AS duplicate_number"
            " FROM checkpoints"
            ") "
            "UPDATE checkpoints "
            "SET code = checkpoints.code || '-' || checkpoints.id "
            "FROM ranked "
            "WHERE checkpoints.id = ranked.id AND ranked.duplicate_number > 1"
        ))
    op.create_unique_constraint(
        'uq_checkpoints_org_code',
        'checkpoints',
        ['organisation_id', 'code'],
    )

    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('leader_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['leader_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'name', name='uq_teams_org_name'),
    )
    for column in (
        'id', 'name', 'leader_user_id', 'status', 'organisation_id',
        'created_at', 'updated_at', 'created_by', 'updated_by', 'is_deleted',
    ):
        op.create_index(f'ix_teams_{column}', 'teams', [column])
    op.alter_column('teams', 'status', server_default=None)
    op.alter_column('teams', 'is_deleted', server_default=None)

    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organisation_id', 'user_id', name='uq_team_members_org_user'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
    )
    for column in ('id', 'team_id', 'user_id', 'organisation_id', 'created_by'):
        op.create_index(f'ix_team_members_{column}', 'team_members', [column])

    op.create_table(
        'patrol_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patrol_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            '(user_id IS NOT NULL AND team_id IS NULL) OR '
            '(user_id IS NULL AND team_id IS NOT NULL)',
            name='ck_patrol_assignment_one_target',
        ),
        sa.ForeignKeyConstraint(['patrol_id'], ['patrols.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patrol_id', 'user_id', name='uq_patrol_assignment_user'),
        sa.UniqueConstraint('patrol_id', 'team_id', name='uq_patrol_assignment_team'),
    )
    for column in ('id', 'patrol_id', 'user_id', 'team_id', 'organisation_id', 'created_by'):
        op.create_index(f'ix_patrol_assignments_{column}', 'patrol_assignments', [column])


def downgrade() -> None:
    op.drop_table('patrol_assignments')
    op.drop_table('team_members')
    op.drop_table('teams')
    op.drop_constraint('uq_checkpoints_org_code', 'checkpoints', type_='unique')
    op.drop_index('ix_alerts_reported_by', table_name='alerts')
    op.drop_index('ix_alerts_category', table_name='alerts')
    op.drop_constraint('fk_alerts_reported_by_users', 'alerts', type_='foreignkey')
    op.drop_column('alerts', 'reported_by')
    op.drop_column('alerts', 'resolution_notes')
    op.drop_column('alerts', 'location')
    op.drop_column('alerts', 'category')
    op.drop_column('patrols', 'required_officers')
    op.drop_constraint('uq_users_org_staff_identifier', 'users', type_='unique')
    op.drop_index('ix_users_staff_identifier', table_name='users')
    op.drop_column('users', 'staff_identifier')
