from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    OrderItem,
    Payout,
    PayoutProfile,
    PayoutRecipientType,
    PayoutStatus,
)


class SupplierPayoutSetupError(Exception):
    pass


def money(value) -> Decimal:
    return Decimal(
        str(value or 0)
    ).quantize(
        Decimal("0.01")
    )


def prepare_supplier_payouts_for_order(
    db: Session,
    order_id: int,
) -> list[Payout]:
    items = list(
        db.scalars(
            select(OrderItem)
            .where(
                OrderItem.order_id
                == order_id
            )
        ).all()
    )

    totals: dict[int, Decimal] = {}

    for item in items:
        if item.supplier_id is None:
            continue

        quantity = money(
            item.confirmed_quantity
        )

        price = money(
            item.confirmed_price
        )

        if (
            quantity <= 0
            or price <= 0
        ):
            continue

        totals[item.supplier_id] = (
            totals.get(
                item.supplier_id,
                Decimal("0.00"),
            )
            + (
                quantity
                * price
            )
        ).quantize(
            Decimal("0.01")
        )

    prepared: list[Payout] = []

    for supplier_id, amount in totals.items():
        existing = db.scalars(
            select(Payout)
            .where(
                Payout.order_id
                == order_id,

                Payout.supplier_id
                == supplier_id,

                Payout.recipient_type
                == PayoutRecipientType.SUPPLIER,
            )
            .order_by(
                Payout.id.desc()
            )
        ).first()

        if existing is not None:
            prepared.append(
                existing
            )
            continue

        profile = db.scalars(
            select(PayoutProfile)
            .where(
                PayoutProfile.recipient_type
                == PayoutRecipientType.SUPPLIER,

                PayoutProfile.supplier_id
                == supplier_id,

                PayoutProfile.is_active
                .is_(True),

                PayoutProfile.is_verified
                .is_(True),

                PayoutProfile.is_locked
                .is_(True),
            )
            .order_by(
                PayoutProfile.id.desc()
            )
        ).first()

        if profile is None:
            raise SupplierPayoutSetupError(
                "Supplier "
                f"#{supplier_id} does not have "
                "an active verified locked "
                "payout profile."
            )

        payout = Payout(
            payout_profile_id=
                profile.id,

            recipient_type=
                PayoutRecipientType.SUPPLIER,

            supplier_id=
                supplier_id,

            driver_id=
                None,

            order_id=
                order_id,

            delivery_batch_id=
                None,

            amount=
                amount,

            currency=
                "GHS",

            reason=
                "supplier_goods",

            client_reference=
                f"sds-{order_id}-{supplier_id}",

            status=
                PayoutStatus.PENDING_APPROVAL,
        )

        db.add(payout)
        db.flush()

        prepared.append(
            payout
        )

    return prepared
