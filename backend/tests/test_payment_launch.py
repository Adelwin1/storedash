from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.main import app, PUBLIC_API_PATHS
from app.models.entities import (
    OrderItem,
    Payout,
    PayoutProfile,
    PayoutRecipientType,
    PayoutStatus,
)
from app.services.sms_payment_relay import (
    message_fingerprint,
    normalize_phone_from_text,
    parse_money_sms,
)
import app.services.supplier_payouts as supplier_payouts


# ============================================================
# SMS RELAY PARSER
# ============================================================


def test_normalizes_ghana_local_phone():
    assert (
        normalize_phone_from_text(
            "024 123 4567"
        )
        == "233241234567"
    )


def test_normalizes_ghana_international_phone():
    assert (
        normalize_phone_from_text(
            "+233 24 123 4567"
        )
        == "233241234567"
    )


def test_parses_incoming_money_sms():
    parsed = parse_money_sms(
        "You have received GHS 420.00 "
        "from 0241234567. "
        "Transaction ID ABC123456."
    )

    assert parsed is not None
    assert parsed.direction == "incoming"
    assert parsed.amount == Decimal("420.00")
    assert parsed.phone == "233241234567"
    assert (
        parsed.transaction_reference
        == "ABC123456"
    )


def test_parses_outgoing_money_sms():
    parsed = parse_money_sms(
        "You sent GH₵35.50 "
        "to 0551234567. "
        "Ref XYZ987654."
    )

    assert parsed is not None
    assert parsed.direction == "outgoing"
    assert parsed.amount == Decimal("35.50")
    assert parsed.phone == "233551234567"
    assert (
        parsed.transaction_reference
        == "XYZ987654"
    )


def test_ignores_non_money_sms():
    assert (
        parse_money_sms(
            "Your data bundle expires tomorrow."
        )
        is None
    )


def test_sms_fingerprint_is_deterministic():
    one = message_fingerprint(
        sender="MTN",
        body="Received GHS 10.00",
        received_at="2026-11-07T10:00:00",
    )

    two = message_fingerprint(
        sender="MTN",
        body="Received GHS 10.00",
        received_at="2026-11-07T10:00:00",
    )

    assert one == two


# ============================================================
# RELAY ROUTE SECURITY / REGISTRATION
# ============================================================


def test_sms_relay_routes_registered():
    paths = {
        route.path
        for route in app.routes
    }

    assert (
        "/api/payments/orders/"
        "{order_id}/expect-sms-payment"
        in paths
    )

    assert (
        "/api/payments/sms-relay/events"
        in paths
    )

    assert (
        "/api/payments/sms-relay/verification"
        in paths
    )

    assert (
        "/api/payments/sms-relay/events/"
        "{event_id}/resolve-incoming"
        in paths
    )


def test_only_phone_ingestion_route_is_public():
    assert (
        "/api/payments/sms-relay/events"
        in PUBLIC_API_PATHS
    )

    assert (
        "/api/payments/sms-relay/verification"
        not in PUBLIC_API_PATHS
    )

    assert (
        "/api/payments/sms-relay/events/"
        "{event_id}/resolve-incoming"
        not in PUBLIC_API_PATHS
    )


# ============================================================
# SUPPLIER PAYOUT CREATION
# ============================================================


class FakeQuery:
    def __init__(self, entity):
        self.entity = entity

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self


class FakeResult:
    def __init__(self, values):
        self.values = list(values)

    def all(self):
        return list(self.values)

    def first(self):
        if not self.values:
            return None

        return self.values[0]


class FakeDB:
    def __init__(
        self,
        *,
        items,
        existing_payout=None,
        profile=None,
    ):
        self.items = list(items)
        self.existing_payout = existing_payout
        self.profile = profile
        self.added = []
        self.flush_count = 0

    def scalars(self, query):
        if query.entity is OrderItem:
            return FakeResult(
                self.items
            )

        if query.entity is Payout:
            return FakeResult(
                []
                if self.existing_payout is None
                else [self.existing_payout]
            )

        if query.entity is PayoutProfile:
            return FakeResult(
                []
                if self.profile is None
                else [self.profile]
            )

        raise AssertionError(
            f"Unexpected query entity: {query.entity}"
        )

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_count += 1


@pytest.fixture
def fake_select(monkeypatch):
    monkeypatch.setattr(
        supplier_payouts,
        "select",
        lambda entity: FakeQuery(entity),
    )


def test_supplier_payout_amount_is_system_calculated(
    fake_select,
):
    item_one = SimpleNamespace(
        supplier_id=7,
        confirmed_quantity=2,
        confirmed_price=Decimal("15.25"),
    )

    item_two = SimpleNamespace(
        supplier_id=7,
        confirmed_quantity=3,
        confirmed_price=Decimal("4.50"),
    )

    profile = SimpleNamespace(
        id=91,
    )

    db = FakeDB(
        items=[
            item_one,
            item_two,
        ],
        profile=profile,
    )

    result = (
        supplier_payouts
        .prepare_supplier_payouts_for_order(
            db,
            44,
        )
    )

    assert len(result) == 1
    assert len(db.added) == 1

    payout = db.added[0]

    assert payout.order_id == 44
    assert payout.supplier_id == 7
    assert payout.payout_profile_id == 91

    assert (
        payout.recipient_type
        == PayoutRecipientType.SUPPLIER
    )

    assert payout.amount == Decimal("44.00")
    assert payout.currency == "GHS"
    assert payout.reason == "supplier_goods"

    assert (
        payout.client_reference
        == "sds-44-7"
    )

    assert (
        payout.status
        == PayoutStatus.PENDING_APPROVAL
    )


def test_supplier_payout_creation_is_idempotent(
    fake_select,
):
    existing = SimpleNamespace(
        id=123,
        amount=Decimal("50.00"),
    )

    db = FakeDB(
        items=[
            SimpleNamespace(
                supplier_id=4,
                confirmed_quantity=1,
                confirmed_price=50,
            )
        ],
        existing_payout=existing,
        profile=None,
    )

    result = (
        supplier_payouts
        .prepare_supplier_payouts_for_order(
            db,
            10,
        )
    )

    assert result == [existing]
    assert db.added == []
    assert db.flush_count == 0


def test_supplier_without_locked_profile_blocks_payout(
    fake_select,
):
    db = FakeDB(
        items=[
            SimpleNamespace(
                supplier_id=5,
                confirmed_quantity=2,
                confirmed_price=25,
            )
        ],
        profile=None,
    )

    with pytest.raises(
        supplier_payouts
        .SupplierPayoutSetupError
    ):
        (
            supplier_payouts
            .prepare_supplier_payouts_for_order(
                db,
                77,
            )
        )

    assert db.added == []
