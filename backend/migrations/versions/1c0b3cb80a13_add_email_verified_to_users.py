"""Add email_verified to users.

Revision ID: 1c0b3cb80a13
Revises: df30a7712012
Create Date: 2026-08-24 16:37:23.234181

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1c0b3cb80a13"
down_revision: Union[str, Sequence[str], None] = "df30a7712012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add a non-null email_verified column.

    Autogenerate alone cannot add NOT NULL to a populated table. We:
    1. Add the column with a temporary server default of true so existing
       accounts remain able to log in after deploy.
    2. Drop the server default so new rows follow the ORM default (false
       until the user confirms their email).
    """
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verified")
