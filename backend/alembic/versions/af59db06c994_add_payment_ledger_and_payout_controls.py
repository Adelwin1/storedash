"""add payment ledger and payout controls

Revision ID: af59db06c994
Revises: 9a55818f72a9
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "af59db06c994"
down_revision = "9a55818f72a9"
branch_labels = None
depends_on = None


PAYMENT_STATUSES = (
    "INITIATED",
    "PENDING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "REFUNDED",
)

RECIPIENT_TYPES = (
    "SUPPLIER",
    "DRIVER",
)

PAYOUT_STATUSES = (
    "PENDING_APPROVAL",
    "APPROVED",
    "PROCESSING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
)


def _enum_types():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        payment_enum = postgresql.ENUM(
            *PAYMENT_STATUSES,
            name="paymentstatus",
        )
        recipient_enum = postgresql.ENUM(
            *RECIPIENT_TYPES,
            name="payoutrecipienttype",
        )
        payout_enum = postgresql.ENUM(
            *PAYOUT_STATUSES,
            name="payoutstatus",
        )

        payment_enum.create(bind, checkfirst=True)
        recipient_enum.create(bind, checkfirst=True)
        payout_enum.create(bind, checkfirst=True)

        return (
            postgresql.ENUM(
                *PAYMENT_STATUSES,
                name="paymentstatus",
                create_type=False,
            ),
            postgresql.ENUM(
                *RECIPIENT_TYPES,
                name="payoutrecipienttype",
                create_type=False,
            ),
            postgresql.ENUM(
                *PAYOUT_STATUSES,
                name="payoutstatus",
                create_type=False,
            ),
        )

    return (
        sa.Enum(*PAYMENT_STATUSES, name="paymentstatus"),
        sa.Enum(*RECIPIENT_TYPES, name="payoutrecipienttype"),
        sa.Enum(*PAYOUT_STATUSES, name="payoutstatus"),
    )


def upgrade():
    payment_status, recipient_type, payout_status = _enum_types()

    op.create_table(
        "payout_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_type", recipient_type, nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("destination_type", sa.String(30), nullable=False),
        sa.Column("payment_phone", sa.String(30), nullable=False),
        sa.Column("payment_name", sa.String(160), nullable=False),
        sa.Column("network", sa.String(40), nullable=True),
        sa.Column("provider_recipient_id", sa.String(160), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by_id", sa.Integer(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["locked_by_id"], ["users.id"]),
    )

    for col in (
        "recipient_type",
        "supplier_id",
        "driver_id",
        "is_verified",
        "is_locked",
        "is_active",
    ):
        op.create_index(
            f"ix_payout_profiles_{col}",
            "payout_profiles",
            [col],
        )

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("client_reference", sa.String(120), nullable=False),
        sa.Column("provider_transaction_id", sa.String(160), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("payment_method", sa.String(40), nullable=False),
        sa.Column("payer_phone", sa.String(30), nullable=True),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("provider_status", sa.String(80), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )

    op.create_index(
        "ix_payment_transactions_order_id",
        "payment_transactions",
        ["order_id"],
    )
    op.create_index(
        "ix_payment_transactions_status",
        "payment_transactions",
        ["status"],
    )
    op.create_index(
        "ix_payment_transactions_client_reference",
        "payment_transactions",
        ["client_reference"],
        unique=True,
    )
    op.create_index(
        "ix_payment_transactions_provider_transaction_id",
        "payment_transactions",
        ["provider_transaction_id"],
        unique=True,
    )

    op.create_table(
        "payouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payout_profile_id", sa.Integer(), nullable=False),
        sa.Column("recipient_type", recipient_type, nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("delivery_batch_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("client_reference", sa.String(120), nullable=False),
        sa.Column("provider_transaction_id", sa.String(160), nullable=True),
        sa.Column("status", payout_status, nullable=False),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["payout_profile_id"], ["payout_profiles.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["delivery_batch_id"], ["delivery_batches.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
    )

    for col in (
        "payout_profile_id",
        "recipient_type",
        "supplier_id",
        "driver_id",
        "order_id",
        "delivery_batch_id",
        "status",
    ):
        op.create_index(
            f"ix_payouts_{col}",
            "payouts",
            [col],
        )

    op.create_index(
        "ix_payouts_client_reference",
        "payouts",
        ["client_reference"],
        unique=True,
    )
    op.create_index(
        "ix_payouts_provider_transaction_id",
        "payouts",
        ["provider_transaction_id"],
        unique=True,
    )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_event_id", sa.String(180), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payment_transaction_id", sa.Integer(), nullable=True),
        sa.Column("payout_id", sa.Integer(), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("is_processed", sa.Boolean(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["payment_transaction_id"],
            ["payment_transactions.id"],
        ),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"]),
    )

    for col in (
        "event_type",
        "payment_transaction_id",
        "payout_id",
        "is_processed",
    ):
        op.create_index(
            f"ix_payment_events_{col}",
            "payment_events",
            [col],
        )

    op.create_index(
        "ix_payment_events_provider_event_id",
        "payment_events",
        ["provider_event_id"],
        unique=True,
    )


def downgrade():
    op.drop_table("payment_events")
    op.drop_table("payouts")
    op.drop_table("payment_transactions")
    op.drop_table("payout_profiles")

    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        postgresql.ENUM(
            *PAYOUT_STATUSES,
            name="payoutstatus",
        ).drop(bind, checkfirst=True)

        postgresql.ENUM(
            *RECIPIENT_TYPES,
            name="payoutrecipienttype",
        ).drop(bind, checkfirst=True)

        postgresql.ENUM(
            *PAYMENT_STATUSES,
            name="paymentstatus",
        ).drop(bind, checkfirst=True)
