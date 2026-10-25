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
