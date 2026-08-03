"""add Phase 1.5 integrity structures

Revision ID: f15a4c9d7e21
Revises: c6b03fd24b2a
Create Date: 2026-08-01

This revision is deliberately compatibility-first: legacy references remain,
canonical references are derived only from same-tenant User/Employee mappings,
and unsafe downgrade refuses instead of discarding integrity history.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f15a4c9d7e21'
down_revision: Union[str, Sequence[str], None] = 'c6b03fd24b2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Frozen schema snapshot generated from app.domain.states.STATE_MACHINES. Legal
# transition edges remain application-owned; these values only protect storage.
STORED_STATES = {
    ('organisations', 'status'): ('active', 'archived', 'suspended'),
    ('customers', 'status'): ('active', 'archived', 'inactive'),
    ('sites', 'status'): ('active', 'archived', 'draft', 'inactive'),
    ('employees', 'status'): ('active', 'archived', 'inactive', 'pending'),
    ('teams', 'status'): ('active', 'archived', 'inactive'),
    ('company_policies', 'status'): ('active', 'approved', 'archived', 'draft', 'superseded'),
    ('post_order_versions', 'status'): ('active', 'approved', 'archived', 'draft', 'superseded'),
    ('qualifications', 'status'): ('active', 'retired'),
    ('licences', 'status'): ('expired', 'pending', 'revoked', 'valid'),
    ('availability_periods', 'status'): ('cancelled', 'confirmed', 'expired', 'proposed'),
    ('leave_periods', 'status'): ('approved', 'cancelled', 'rejected', 'requested'),
    ('shifts', 'status'): ('active', 'archived', 'cancelled', 'completed', 'draft', 'published'),
    ('shift_assignments', 'status'): ('active', 'cancelled', 'completed', 'confirmed', 'proposed'),
    ('patrol_templates', 'status'): ('active', 'draft', 'retired', 'superseded'),
    ('patrols', 'lifecycle_status'): ('archived', 'cancelled', 'completed', 'draft', 'in_progress', 'missed', 'scheduled'),
    ('alerts', 'status'): ('cancelled', 'investigating', 'open', 'resolved'),
    ('operational_alerts', 'status'): ('acknowledged', 'expired', 'open', 'resolved'),
    ('notifications', 'delivery_status'): ('delivered', 'failed', 'queued', 'read', 'sent'),
    ('evidence_attachments', 'status'): ('available', 'failed', 'pending', 'quarantined', 'superseded', 'uploading'),
    ('daily_activity_reports', 'status'): ('approved', 'delivered', 'draft', 'generated', 'superseded'),
}

STATE_CONSTRAINT_NAMES = {
    ('organisations', 'status'): 'ck_organisations_status',
    ('customers', 'status'): 'ck_customers_status',
    ('sites', 'status'): 'ck_sites_status',
    ('employees', 'status'): 'ck_employees_status',
    ('teams', 'status'): 'ck_teams_status',
    ('company_policies', 'status'): 'ck_company_policies_status',
    ('post_order_versions', 'status'): 'ck_post_order_versions_status',
    ('qualifications', 'status'): 'ck_qualifications_status',
    ('licences', 'status'): 'ck_licences_status',
    ('availability_periods', 'status'): 'ck_availability_periods_status',
    ('leave_periods', 'status'): 'ck_leave_periods_status',
    ('shifts', 'status'): 'ck_shifts_status',
    ('shift_assignments', 'status'): 'ck_shift_assignments_status',
    ('patrol_templates', 'status'): 'ck_patrol_templates_status',
    ('patrols', 'lifecycle_status'): 'ck_patrols_lifecycle_status',
    ('alerts', 'status'): 'ck_alerts_status',
    ('operational_alerts', 'status'): 'ck_operational_alerts_status',
    ('notifications', 'delivery_status'): 'ck_notifications_delivery_status',
    ('evidence_attachments', 'status'): 'ck_evidence_attachments_status',
    ('daily_activity_reports', 'status'): 'ck_daily_activity_reports_status',
}

VERSIONED_TABLES = (
    'organisations', 'customers', 'sites', 'employees', 'teams',
    'shift_assignments', 'patrol_templates', 'operational_alerts',
    'notifications', 'evidence_attachments', 'daily_activity_reports',
    'company_policies', 'post_orders', 'post_order_versions',
)


def _scalar(bind, sql, params=None):
    return bind.execute(sa.text(sql), params or {}).scalar()


def _refuse(message):
    raise RuntimeError(f'Phase 1.5 integrity migration refused: {message}')


def _preflight(bind):
    for (table, column), allowed in STORED_STATES.items():
        # Customer status is introduced by this revision.
        if table == 'customers':
            continue
        values = bind.execute(sa.text(
            f'SELECT DISTINCT {column} FROM {table} '
            f'WHERE {column} IS NULL OR {column} NOT IN :allowed'
        ).bindparams(sa.bindparam('allowed', expanding=True)), {'allowed': allowed}).scalars().all()
        if values:
            _refuse(f'{table}.{column} contains unsupported values: {values!r}')

    duplicate_policy = _scalar(bind, """
        SELECT COUNT(*) FROM (
          SELECT organisation_id, policy_type FROM company_policies
          WHERE status = 'active' GROUP BY organisation_id, policy_type HAVING COUNT(*) > 1
        ) AS duplicates
    """)
    duplicate_orders = _scalar(bind, """
        SELECT COUNT(*) FROM (
          SELECT organisation_id, post_order_id FROM post_order_versions
          WHERE status = 'active' GROUP BY organisation_id, post_order_id HAVING COUNT(*) > 1
        ) AS duplicates
    """)
    if duplicate_policy or duplicate_orders:
        _refuse('ambiguous active Company Policy or Post Order versions exist')

    for table, user_column in (
        ('team_members', 'user_id'),
        ('patrol_assignments', 'user_id'),
        ('officer_locations', 'officer_user_id'),
    ):
        unmapped = _scalar(bind, f"""
            SELECT COUNT(*) FROM {table} bridge
            WHERE bridge.{user_column} IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM employees employee
                WHERE employee.user_id = bridge.{user_column}
                  AND employee.organisation_id = bridge.organisation_id
              )
        """)
        if unmapped:
            _refuse(f'{unmapped} {table} rows have no deterministic same-tenant Employee mapping')


def _add_version(table):
    op.add_column(table, sa.Column('record_version', sa.Integer(), server_default='1', nullable=False))
    op.create_check_constraint(f'ck_{table}_record_version', table, 'record_version >= 1')
    op.alter_column(table, 'record_version', server_default=None)


def _add_state_constraints(bind):
    # SQLite cannot add named CHECK constraints without rebuilding tables. Its
    # Base.metadata test schema contains the same checks; PostgreSQL migration
    # tests are authoritative for populated upgrades.
    if bind.dialect.name == 'sqlite':
        return
    for key, allowed in STORED_STATES.items():
        table, column = key
        quoted = ', '.join("'" + value.replace("'", "''") + "'" for value in allowed)
        op.create_check_constraint(STATE_CONSTRAINT_NAMES[key], table, f'{column} IN ({quoted})')


def _add_tenant_constraints(bind):
    if bind.dialect.name != 'postgresql':
        return
    unique_pairs = (
        ('customers', 'uq_customers_tenant_id'), ('sites', 'uq_sites_tenant_id'),
        ('employees', 'uq_employees_tenant_id'), ('teams', 'uq_teams_tenant_id'),
        ('shifts', 'uq_shifts_tenant_id'),
        ('patrols', 'uq_patrols_tenant_id'), ('domain_objects', 'uq_domain_objects_tenant_id'),
        ('evidence_attachments', 'uq_evidence_attachments_tenant_id'),
        ('checkpoint_verification_events', 'uq_checkpoint_verification_events_tenant_id'),
        ('post_orders', 'uq_post_orders_tenant_id'),
        ('post_order_versions', 'uq_post_order_versions_tenant_id'),
    )
    for table, name in unique_pairs:
        op.create_unique_constraint(name, table, ['organisation_id', 'id'])

    relationships = (
        ('fk_sites_tenant_customer', 'sites', 'customers', ['organisation_id', 'customer_id']),
        ('fk_team_members_tenant_employee', 'team_members', 'employees', ['organisation_id', 'employee_id']),
        ('fk_patrol_assignments_tenant_employee', 'patrol_assignments', 'employees', ['organisation_id', 'employee_id']),
        ('fk_officer_locations_tenant_employee', 'officer_locations', 'employees', ['organisation_id', 'employee_id']),
        ('fk_evidence_links_tenant_attachment', 'evidence_links', 'evidence_attachments', ['organisation_id', 'evidence_attachment_id']),
        ('fk_evidence_links_tenant_domain_object', 'evidence_links', 'domain_objects', ['organisation_id', 'domain_object_id']),
        ('fk_event_subjects_tenant_domain_object', 'operational_event_subjects', 'domain_objects', ['organisation_id', 'domain_object_id']),
    )
    for name, source, target, columns in relationships:
        op.create_foreign_key(name, source, target, columns, ['organisation_id', 'id'])
    op.create_foreign_key(
        'fk_checkpoint_verification_tenant_correction', 'checkpoint_verification_events',
        'checkpoint_verification_events', ['organisation_id', 'correction_of_id'],
        ['organisation_id', 'id'],
    )
    op.create_foreign_key(
        'fk_checkpoint_verification_tenant_original', 'checkpoint_verification_events',
        'checkpoint_verification_events', ['organisation_id', 'original_event_id'],
        ['organisation_id', 'id'],
    )
    op.create_foreign_key(
        'fk_evidence_tenant_correction', 'evidence_attachments', 'evidence_attachments',
        ['organisation_id', 'correction_of_id'], ['organisation_id', 'id'],
    )


def upgrade() -> None:
    bind = op.get_bind()
    _preflight(bind)

    op.add_column('customers', sa.Column('status', sa.String(), server_default='active', nullable=False))
    op.create_index('ix_customers_status', 'customers', ['status'])

    for table in VERSIONED_TABLES:
        _add_version(table)

    for table, user_column in (
        ('team_members', 'user_id'),
        ('patrol_assignments', 'user_id'),
        ('officer_locations', 'officer_user_id'),
    ):
        op.add_column(table, sa.Column('employee_id', sa.Integer(), nullable=True))
        op.add_column(table, sa.Column(
            'employee_reference_source', sa.String(), server_default='legacy_user_only', nullable=False,
        ))
        op.create_index(f'ix_{table}_employee_id', table, ['employee_id'])
        op.create_index(f'ix_{table}_employee_reference_source', table, ['employee_reference_source'])
        op.create_foreign_key(f'fk_{table}_employee_id', table, 'employees', ['employee_id'], ['id'])
        bind.execute(sa.text(f"""
            UPDATE {table} AS bridge SET
              employee_id = employee.id,
              employee_reference_source = 'canonical_user_mapping'
            FROM employees AS employee
            WHERE employee.user_id = bridge.{user_column}
              AND employee.organisation_id = bridge.organisation_id
        """)) if bind.dialect.name == 'postgresql' else bind.execute(sa.text(f"""
            UPDATE {table} SET
              employee_id = (
                SELECT employee.id FROM employees AS employee
                WHERE employee.user_id = {table}.{user_column}
                  AND employee.organisation_id = {table}.organisation_id
              ),
              employee_reference_source = CASE WHEN EXISTS (
                SELECT 1 FROM employees AS employee
                WHERE employee.user_id = {table}.{user_column}
                  AND employee.organisation_id = {table}.organisation_id
              ) THEN 'canonical_user_mapping' ELSE 'legacy_user_only' END
        """))
        remaining = _scalar(bind, f'SELECT COUNT(*) FROM {table} WHERE {user_column} IS NOT NULL AND employee_id IS NULL')
        if remaining:
            _refuse(f'{remaining} {table} rows failed canonical Employee backfill verification')
        op.alter_column(table, 'employee_reference_source', server_default=None)

    op.create_unique_constraint('uq_team_members_team_employee', 'team_members', ['team_id', 'employee_id'])
    op.create_unique_constraint('uq_patrol_assignment_employee', 'patrol_assignments', ['patrol_id', 'employee_id'])

    op.add_column('patrols', sa.Column('operational_snapshot', sa.JSON(), nullable=True))

    for column in (
        sa.Column('event_kind', sa.String(), server_default='original', nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('correction_of_id', sa.Integer(), nullable=True),
        sa.Column('original_event_id', sa.Integer(), nullable=True),
        sa.Column('record_provenance', sa.String(), server_default='legacy_low_assurance', nullable=False),
        sa.Column('context_snapshot', sa.JSON(), nullable=True),
    ):
        op.add_column('checkpoint_verification_events', column)
    for column in ('event_kind', 'idempotency_key', 'correction_of_id', 'original_event_id', 'record_provenance'):
        op.create_index(f'ix_checkpoint_verification_events_{column}', 'checkpoint_verification_events', [column])
    op.create_foreign_key('fk_checkpoint_verification_correction', 'checkpoint_verification_events', 'checkpoint_verification_events', ['correction_of_id'], ['id'])
    op.create_foreign_key('fk_checkpoint_verification_original', 'checkpoint_verification_events', 'checkpoint_verification_events', ['original_event_id'], ['id'])
    op.create_check_constraint('ck_checkpoint_verification_not_self_correction', 'checkpoint_verification_events', 'correction_of_id IS NULL OR correction_of_id <> id')
    op.create_check_constraint('ck_checkpoint_verification_event_kind', 'checkpoint_verification_events', "event_kind IN ('original', 'correction')")
    op.alter_column('checkpoint_verification_events', 'event_kind', server_default=None)
    op.alter_column('checkpoint_verification_events', 'record_provenance', server_default=None)

    evidence_columns = (
        sa.Column('correction_of_id', sa.Integer(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_by_employee_id', sa.Integer(), nullable=True),
        sa.Column('immutable_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acceptance_version', sa.Integer(), nullable=True),
    )
    for column in evidence_columns:
        op.add_column('evidence_attachments', column)
    for column in ('correction_of_id', 'accepted_at', 'accepted_by_employee_id', 'immutable_at', 'archived_at'):
        op.create_index(f'ix_evidence_attachments_{column}', 'evidence_attachments', [column])
    op.create_foreign_key('fk_evidence_attachments_correction', 'evidence_attachments', 'evidence_attachments', ['correction_of_id'], ['id'])
    op.create_foreign_key('fk_evidence_attachments_accepted_by_employee', 'evidence_attachments', 'employees', ['accepted_by_employee_id'], ['id'])
    op.create_check_constraint('ck_evidence_not_self_correction', 'evidence_attachments', 'correction_of_id IS NULL OR correction_of_id <> id')

    report_columns = (
        sa.Column('correction_of_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_employee_id', sa.Integer(), nullable=True),
        sa.Column('snapshot_checksum', sa.String(), nullable=True),
        sa.Column('site_snapshot', sa.JSON(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_version', sa.Integer(), nullable=True),
    )
    for column in report_columns:
        op.add_column('daily_activity_reports', column)
    for column in ('correction_of_id', 'approved_by_employee_id', 'snapshot_checksum', 'archived_at'):
        op.create_index(f'ix_daily_activity_reports_{column}', 'daily_activity_reports', [column])
    op.create_foreign_key('fk_daily_reports_correction', 'daily_activity_reports', 'daily_activity_reports', ['correction_of_id'], ['id'])
    op.create_foreign_key('fk_daily_reports_approved_by_employee', 'daily_activity_reports', 'employees', ['approved_by_employee_id'], ['id'])
    op.create_check_constraint('ck_daily_report_not_self_correction', 'daily_activity_reports', 'correction_of_id IS NULL OR correction_of_id <> id')

    op.add_column('post_order_versions', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('post_order_versions', sa.Column('content_checksum', sa.String(), nullable=True))
    op.create_index('ix_post_order_versions_archived_at', 'post_order_versions', ['archived_at'])
    op.create_index('ix_post_order_versions_content_checksum', 'post_order_versions', ['content_checksum'])

    op.create_table(
        'idempotency_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organisation_id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('actor_scope', sa.String(), nullable=False),
        sa.Column('idempotency_key', sa.String(), nullable=False),
        sa.Column('command_type', sa.String(), nullable=False),
        sa.Column('request_fingerprint', sa.String(), nullable=False),
        sa.Column('processing_state', sa.String(), server_default='pending', nullable=False),
        sa.Column('result_object_type', sa.String(), nullable=True),
        sa.Column('result_object_id', sa.Integer(), nullable=True),
        sa.Column('response_metadata', sa.JSON(), nullable=True),
        sa.Column('failure_code', sa.String(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('record_version', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], name='fk_idempotency_records_organisation'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name='fk_idempotency_records_actor_user'),
        sa.UniqueConstraint('organisation_id', 'actor_scope', 'command_type', 'idempotency_key', name='uq_idempotency_command_scope'),
        sa.CheckConstraint("processing_state IN ('pending', 'completed', 'failed')", name='ck_idempotency_records_processing_state'),
        sa.CheckConstraint('record_version >= 1', name='ck_idempotency_records_record_version'),
    )
    for column in ('organisation_id', 'actor_user_id', 'command_type', 'processing_state', 'correlation_id', 'created_at', 'expires_at'):
        op.create_index(f'ix_idempotency_records_{column}', 'idempotency_records', [column])
    op.alter_column('idempotency_records', 'processing_state', server_default=None)
    op.alter_column('idempotency_records', 'created_at', server_default=None)
    op.alter_column('idempotency_records', 'record_version', server_default=None)

    op.create_index(
        'uq_company_policies_active_scope', 'company_policies', ['organisation_id', 'policy_type'],
        unique=True, postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index(
        'uq_post_order_versions_active_scope', 'post_order_versions', ['organisation_id', 'post_order_id'],
        unique=True, postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"),
    )

    _add_state_constraints(bind)
    _add_tenant_constraints(bind)
    op.alter_column('customers', 'status', server_default=None)


def _downgrade_preflight(bind):
    hazards = []
    if _scalar(bind, 'SELECT COUNT(*) FROM idempotency_records'):
        hazards.append('idempotency ledger is not empty')
    for table in VERSIONED_TABLES:
        if _scalar(bind, f'SELECT COUNT(*) FROM {table} WHERE record_version <> 1'):
            hazards.append(f'{table} contains post-migration versions')
    for table, user_column in (
        ('team_members', 'user_id'), ('patrol_assignments', 'user_id'),
        ('officer_locations', 'officer_user_id'),
    ):
        if _scalar(bind, f"""
            SELECT COUNT(*) FROM {table} bridge
            WHERE employee_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM employees employee
              WHERE employee.id = bridge.employee_id
                AND employee.user_id = bridge.{user_column}
                AND employee.organisation_id = bridge.organisation_id
            )
        """):
            hazards.append(f'{table} contains Employee-native references')
    metadata_checks = {
        'checkpoint_verification_events': "correction_of_id IS NOT NULL OR original_event_id IS NOT NULL OR idempotency_key IS NOT NULL OR context_snapshot IS NOT NULL OR record_provenance <> 'legacy_low_assurance'",
        'evidence_attachments': 'correction_of_id IS NOT NULL OR accepted_at IS NOT NULL OR accepted_by_employee_id IS NOT NULL OR immutable_at IS NOT NULL OR archived_at IS NOT NULL OR acceptance_version IS NOT NULL',
        'daily_activity_reports': 'correction_of_id IS NOT NULL OR approved_by_employee_id IS NOT NULL OR snapshot_checksum IS NOT NULL OR site_snapshot IS NOT NULL OR archived_at IS NOT NULL OR approval_version IS NOT NULL',
        'post_order_versions': 'archived_at IS NOT NULL OR content_checksum IS NOT NULL',
        'patrols': 'operational_snapshot IS NOT NULL',
    }
    for table, predicate in metadata_checks.items():
        if _scalar(bind, f'SELECT COUNT(*) FROM {table} WHERE {predicate}'):
            hazards.append(f'{table} contains Phase 1.5 integrity metadata')
    if hazards:
        _refuse('unsafe downgrade: ' + '; '.join(hazards))


def downgrade() -> None:
    bind = op.get_bind()
    _downgrade_preflight(bind)

    if bind.dialect.name == 'postgresql':
        for name, table in (
            ('fk_evidence_tenant_correction', 'evidence_attachments'),
            ('fk_checkpoint_verification_tenant_original', 'checkpoint_verification_events'),
            ('fk_checkpoint_verification_tenant_correction', 'checkpoint_verification_events'),
            ('fk_event_subjects_tenant_domain_object', 'operational_event_subjects'),
            ('fk_evidence_links_tenant_domain_object', 'evidence_links'),
            ('fk_evidence_links_tenant_attachment', 'evidence_links'),
            ('fk_officer_locations_tenant_employee', 'officer_locations'),
            ('fk_patrol_assignments_tenant_employee', 'patrol_assignments'),
            ('fk_team_members_tenant_employee', 'team_members'),
            ('fk_sites_tenant_customer', 'sites'),
        ):
            op.drop_constraint(name, table, type_='foreignkey')
        for table, name in (
            ('post_order_versions', 'uq_post_order_versions_tenant_id'),
            ('post_orders', 'uq_post_orders_tenant_id'),
            ('checkpoint_verification_events', 'uq_checkpoint_verification_events_tenant_id'),
            ('evidence_attachments', 'uq_evidence_attachments_tenant_id'),
            ('domain_objects', 'uq_domain_objects_tenant_id'), ('patrols', 'uq_patrols_tenant_id'),
            ('shifts', 'uq_shifts_tenant_id'), ('teams', 'uq_teams_tenant_id'),
            ('employees', 'uq_employees_tenant_id'),
            ('sites', 'uq_sites_tenant_id'), ('customers', 'uq_customers_tenant_id'),
        ):
            op.drop_constraint(name, table, type_='unique')
        for key, name in reversed(tuple(STATE_CONSTRAINT_NAMES.items())):
            op.drop_constraint(name, key[0], type_='check')

    op.drop_index('uq_post_order_versions_active_scope', table_name='post_order_versions')
    op.drop_index('uq_company_policies_active_scope', table_name='company_policies')
    op.drop_table('idempotency_records')

    op.drop_index('ix_post_order_versions_content_checksum', table_name='post_order_versions')
    op.drop_index('ix_post_order_versions_archived_at', table_name='post_order_versions')
    op.drop_column('post_order_versions', 'content_checksum')
    op.drop_column('post_order_versions', 'archived_at')

    for table, columns, constraints in (
        ('daily_activity_reports', ('approval_version', 'archived_at', 'site_snapshot', 'snapshot_checksum', 'approved_by_employee_id', 'correction_of_id'), ('ck_daily_report_not_self_correction', 'fk_daily_reports_approved_by_employee', 'fk_daily_reports_correction')),
        ('evidence_attachments', ('acceptance_version', 'archived_at', 'immutable_at', 'accepted_by_employee_id', 'accepted_at', 'correction_of_id'), ('ck_evidence_not_self_correction', 'fk_evidence_attachments_accepted_by_employee', 'fk_evidence_attachments_correction')),
    ):
        for name in constraints:
            kind = 'check' if name.startswith('ck_') else 'foreignkey'
            op.drop_constraint(name, table, type_=kind)
        for column in columns:
            index = f'ix_{table}_{column}'
            if column not in ('approval_version', 'site_snapshot', 'acceptance_version'):
                op.drop_index(index, table_name=table)
            op.drop_column(table, column)

    op.drop_constraint('ck_checkpoint_verification_event_kind', 'checkpoint_verification_events', type_='check')
    op.drop_constraint('ck_checkpoint_verification_not_self_correction', 'checkpoint_verification_events', type_='check')
    op.drop_constraint('fk_checkpoint_verification_original', 'checkpoint_verification_events', type_='foreignkey')
    op.drop_constraint('fk_checkpoint_verification_correction', 'checkpoint_verification_events', type_='foreignkey')
    for column in ('record_provenance', 'original_event_id', 'correction_of_id', 'idempotency_key', 'event_kind'):
        op.drop_index(f'ix_checkpoint_verification_events_{column}', table_name='checkpoint_verification_events')
    for column in ('context_snapshot', 'record_provenance', 'original_event_id', 'correction_of_id', 'idempotency_key', 'event_kind'):
        op.drop_column('checkpoint_verification_events', column)

    op.drop_column('patrols', 'operational_snapshot')
    op.drop_constraint('uq_patrol_assignment_employee', 'patrol_assignments', type_='unique')
    op.drop_constraint('uq_team_members_team_employee', 'team_members', type_='unique')
    for table in ('officer_locations', 'patrol_assignments', 'team_members'):
        op.drop_constraint(f'fk_{table}_employee_id', table, type_='foreignkey')
        op.drop_index(f'ix_{table}_employee_reference_source', table_name=table)
        op.drop_index(f'ix_{table}_employee_id', table_name=table)
        op.drop_column(table, 'employee_reference_source')
        op.drop_column(table, 'employee_id')

    for table in reversed(VERSIONED_TABLES):
        op.drop_constraint(f'ck_{table}_record_version', table, type_='check')
        op.drop_column(table, 'record_version')
    op.drop_index('ix_customers_status', table_name='customers')
    op.drop_column('customers', 'status')
