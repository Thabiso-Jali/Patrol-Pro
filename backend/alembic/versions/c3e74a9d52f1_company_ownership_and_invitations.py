"""Add company ownership, revocable sessions, and employee invitations.

Revision ID: c3e74a9d52f1
Revises: 7a28f92acb7e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e74a9d52f1"
down_revision: Union[str, Sequence[str], None] = "7a28f92acb7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = (
    "users", "customers", "devices", "patrols", "alerts", "checkpoints",
    "incidents", "notifications", "officer_locations", "patrol_logs",
)


def upgrade() -> None:
    for name, type_, kwargs in (
        ("business_email", sa.String(), {"nullable": True}),
        ("registration_number", sa.String(), {"nullable": True}),
        ("vat_number", sa.String(), {"nullable": True}),
        ("tax_number", sa.String(), {"nullable": True}),
        ("address", sa.Text(), {"nullable": True}),
        ("country", sa.String(), {"nullable": True}),
        ("timezone", sa.String(), {"nullable": False, "server_default": "UTC"}),
        ("industry", sa.String(), {"nullable": True}),
        ("phone", sa.String(), {"nullable": True}),
        ("subscription_plan", sa.String(), {"nullable": False, "server_default": "pilot"}),
        ("permission_version", sa.Integer(), {"nullable": False, "server_default": "1"}),
        ("status", sa.String(), {"nullable": False, "server_default": "active"}),
    ):
        op.add_column("organisations", sa.Column(name, type_, **kwargs))
    op.create_index(op.f("ix_organisations_status"), "organisations", ["status"])
    for column in ("timezone", "subscription_plan", "permission_version", "status"):
        op.alter_column("organisations", column, server_default=None)

    for name, type_, kwargs in (
        ("is_active", sa.Boolean(), {"nullable": False, "server_default": sa.true()}),
        ("session_version", sa.Integer(), {"nullable": False, "server_default": "1"}),
        ("permission_version", sa.Integer(), {"nullable": False, "server_default": "1"}),
        ("failed_login_attempts", sa.Integer(), {"nullable": False, "server_default": "0"}),
        ("locked_until", sa.DateTime(), {"nullable": True}),
        ("last_login_at", sa.DateTime(), {"nullable": True}),
    ):
        op.add_column("users", sa.Column(name, type_, **kwargs))
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"])
    op.create_index(op.f("ix_users_locked_until"), "users", ["locked_until"])
    for column in ("is_active", "session_version", "permission_version", "failed_login_attempts"):
        op.alter_column("users", column, server_default=None)

    connection = op.get_bind()
    for table in TENANT_TABLES:
        missing = connection.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE organisation_id IS NULL")
        ).scalar_one()
        if missing:
            raise RuntimeError(
                f"{table} has {missing} unscoped row(s); assign them to the correct company before upgrading"
            )
        op.alter_column(table, "organisation_id", existing_type=sa.Integer(), nullable=False)

    op.add_column("audit_logs", sa.Column("organisation_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_audit_logs_organisation_id_organisations",
        "audit_logs", "organisations", ["organisation_id"], ["id"],
    )
    connection.execute(sa.text(
        "UPDATE audit_logs SET organisation_id = users.organisation_id "
        "FROM users WHERE audit_logs.actor_user_id = users.id"
    ))
    unscoped_audit = connection.execute(
        sa.text("SELECT COUNT(*) FROM audit_logs WHERE organisation_id IS NULL")
    ).scalar_one()
    if unscoped_audit:
        raise RuntimeError(
            f"audit_logs has {unscoped_audit} unscoped row(s); assign them before upgrading"
        )
    op.alter_column("audit_logs", "organisation_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_audit_logs_organisation_id"), "audit_logs", ["organisation_id"])

    op.create_table(
        "employee_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("invited_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
    )
    for column in ("organisation_id", "email", "role", "expires_at", "accepted_at", "invited_by", "created_at"):
        op.create_index(op.f(f"ix_employee_invitations_{column}"), "employee_invitations", [column])
    op.create_index(
        op.f("ix_employee_invitations_token_hash"),
        "employee_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "uq_active_invitation_company_email",
        "employee_invitations",
        ["organisation_id", "email"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("employee_invitations")
    op.drop_column("audit_logs", "organisation_id")
    for table in reversed(TENANT_TABLES):
        op.alter_column(table, "organisation_id", existing_type=sa.Integer(), nullable=True)
    for column in ("last_login_at", "locked_until", "failed_login_attempts", "permission_version", "session_version", "is_active"):
        op.drop_column("users", column)
    for column in (
        "status", "permission_version", "subscription_plan", "phone", "industry",
        "timezone", "country", "address", "tax_number", "vat_number",
        "registration_number", "business_email",
    ):
        op.drop_column("organisations", column)
