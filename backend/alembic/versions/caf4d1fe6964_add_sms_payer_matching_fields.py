"""add sms payer matching fields

Revision ID: caf4d1fe6964
Revises: af59db06c994
Create Date: 2026-11-08 02:43:46.802294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caf4d1fe6964'
down_revision: Union[str, Sequence[str], None] = 'af59db06c994'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_transactions",
        sa.Column(
            "expected_payer_name",
            sa.String(length=160),
            nullable=True,
        ),
    )
    op.add_column(
        "payment_transactions",
        sa.Column(
            "received_payer_name",
            sa.String(length=160),
            nullable=True,
        ),
    )
    op.add_column(
        "payment_transactions",
        sa.Column(
            "received_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "payment_transactions",
        "received_amount",
    )
    op.drop_column(
        "payment_transactions",
        "received_payer_name",
    )
    op.drop_column(
        "payment_transactions",
        "expected_payer_name",
    )
