from fastapi.testclient import TestClient

from app.main import app, role_can_access
from app.models.entities import Role


client = TestClient(app)


def test_health_is_public():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_orders_require_authentication():
    response = client.get("/api/orders")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_operations_can_access_orders():
    assert role_can_access(
        Role.OPERATIONS,
        "GET",
        "/api/orders",
    )


def test_operations_cannot_manage_users():
    assert not role_can_access(
        Role.OPERATIONS,
        "GET",
        "/api/users",
    )


def test_manager_can_manage_users():
    assert role_can_access(
        Role.MANAGER,
        "GET",
        "/api/users",
    )


def test_supplier_field_access_is_limited():
    assert role_can_access(
        Role.SUPPLIER_FIELD,
        "GET",
        "/api/suppliers",
    )

    assert not role_can_access(
        Role.SUPPLIER_FIELD,
        "GET",
        "/api/orders",
    )


def test_payment_request_requires_authentication():
    response = client.post(
        "/api/payments/orders/1/request",
        json={
            "customer_phone": "0241234567",
            "network": "mtn",
        },
    )

    assert response.status_code == 401


def test_operations_can_access_payment_operations():
    assert role_can_access(
        Role.OPERATIONS,
        "POST",
        "/api/payments/orders/1/request",
    )


def test_field_staff_cannot_access_payment_operations():
    assert not role_can_access(
        Role.SUPPLIER_FIELD,
        "POST",
        "/api/payments/orders/1/request",
    )

    assert not role_can_access(
        Role.CUSTOMER_FIELD,
        "POST",
        "/api/payments/orders/1/request",
    )

    assert not role_can_access(
        Role.ACQUISITION,
        "POST",
        "/api/payments/orders/1/request",
    )


def test_hubtel_callbacks_are_public_provider_paths():
    from app.main import PUBLIC_API_PATHS

    assert (
        "/api/payments/hubtel/collections/callback"
        in PUBLIC_API_PATHS
    )

    assert (
        "/api/payments/hubtel/payouts/callback"
        in PUBLIC_API_PATHS
    )

    assert (
        "/api/payments/orders/1/request"
        not in PUBLIC_API_PATHS
    )


def test_manual_payment_confirmation_is_disabled():
    from fastapi import HTTPException

    from app.api.routes.order_workflow import (
        confirm_payment,
    )

    try:
        confirm_payment(
            order_id=1,
            payload=None,
            db=None,
        )
    except HTTPException as exc:
        assert exc.status_code == 410
        assert (
            "Manual payment confirmation is disabled"
            in str(exc.detail)
        )
    else:
        raise AssertionError(
            "Manual payment confirmation unexpectedly remained enabled."
        )



def test_last_active_admin_requires_replacement():
    from app.api.routes.auth import (
        admin_replacement_required,
    )

    assert admin_replacement_required(
        target_role=Role.ADMIN,
        target_is_active=True,
        active_admin_count=1,
    )


def test_admin_can_be_deactivated_when_another_admin_exists():
    from app.api.routes.auth import (
        admin_replacement_required,
    )

    assert not admin_replacement_required(
        target_role=Role.ADMIN,
        target_is_active=True,
        active_admin_count=2,
    )


def test_non_admin_never_requires_admin_replacement():
    from app.api.routes.auth import (
        admin_replacement_required,
    )

    assert not admin_replacement_required(
        target_role=Role.OPERATIONS,
        target_is_active=True,
        active_admin_count=1,
    )
