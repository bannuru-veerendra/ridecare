"""Add email reminder preference columns to users.

Revision ID: 2fefc94abc4b
Revises: 1c0b3cb80a13
Create Date: 2026-09-03 15:53:03.585508
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2fefc94abc4b"
down_revision: Union[str, Sequence[str], None] = "1c0b3cb80a13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Existing accounts opt in to reminder emails by default.

    Temporary server_default=true backfills rows; then drop it so new
    inserts follow the ORM default (also true).
    """
    op.add_column(
        "users",
        sa.Column(
            "email_service_reminders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_document_reminders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("users", "email_service_reminders", server_default=None)
    op.alter_column("users", "email_document_reminders", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_document_reminders")
    op.drop_column("users", "email_service_reminders")
