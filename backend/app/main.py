from fastapi import FastAPI, Request

from fastapi.responses import JSONResponse

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.routes import auth
from app.api.routes import batching
from app.api.routes import (
    businesses,
    business_suppliers,
    customer_insights,
    drivers,
    driver_negotiation,
    driver_operations,
    delivery_market,
    health,
    logistics,
    locations,
    operating_days,
    order_workflow,
    order_logistics,
    orders,
    suppliers,
    users,
)

from app.core.config import get_settings
from app.core.db import Base, engine, SessionLocal
from app.core.auth import authenticate_request
from app.models.entities import Role

import app.models  # noqa: F401


settings = get_settings()


app = FastAPI(
    title="StoreDash Operations API",
    version="0.2.0",
    description=(
        "Internal StoreDash "
        "operations platform."
    ),
)




PUBLIC_API_PATHS = {
    "/api/auth/login",
    "/api/auth/signup",
}


AUTHENTICATED_SHARED_PATHS = {
    "/api/auth/me",
    "/api/auth/logout",
}


ADMIN_ONLY_PREFIXES = (
    "/api/auth/approved-employees",
)


ADMIN_MANAGER_PREFIXES = (
    "/api/users",
)


FIELD_ACCESS = {
    Role.SUPPLIER_FIELD: (
        ("GET", "/api/suppliers"),
        ("POST", "/api/suppliers"),
        ("PATCH", "/api/suppliers"),
        ("GET", "/api/locations"),
    ),

    Role.CUSTOMER_FIELD: (
        ("GET", "/api/businesses"),
        ("POST", "/api/businesses"),
        ("PATCH", "/api/businesses"),
        ("GET", "/api/locations"),
    ),

    Role.ACQUISITION: (
        ("GET", "/api/suppliers"),
        ("POST", "/api/suppliers"),
        ("PATCH", "/api/suppliers"),
        ("GET", "/api/businesses"),
        ("POST", "/api/businesses"),
        ("PATCH", "/api/businesses"),
        ("GET", "/api/locations"),
    ),
}


def role_can_access(
    role: Role,
    method: str,
    path: str,
) -> bool:

    if path in AUTHENTICATED_SHARED_PATHS:
        return True

    if any(
        path.startswith(prefix)
        for prefix in ADMIN_ONLY_PREFIXES
    ):
        return role == Role.ADMIN

    if any(
        path.startswith(prefix)
        for prefix in ADMIN_MANAGER_PREFIXES
    ):
        return role in {
            Role.ADMIN,
            Role.MANAGER,
        }

    if role in {
        Role.ADMIN,
        Role.MANAGER,
        Role.OPERATIONS,
    }:
        return True

    for (
        allowed_method,
        allowed_prefix,
    ) in FIELD_ACCESS.get(
        role,
        (),
    ):
        if (
            method == allowed_method
            and path.startswith(
                allowed_prefix
            )
        ):
            return True

    return False


@app.middleware("http")
async def require_storedash_login(
    request: Request,
    call_next,
):

    path = request.url.path

    if request.method == "OPTIONS":
        return await call_next(
            request
        )

    if not path.startswith(
        "/api/"
    ):
        return await call_next(
            request
        )

    if path in PUBLIC_API_PATHS:
        return await call_next(
            request
        )

    db = SessionLocal()

    try:

        user = authenticate_request(
            request,
            db,
        )

        if user is None:
            return JSONResponse(
                status_code=401,
                content={
                    "detail":
                        "Authentication required."
                },
            )

        request.state.user_id = (
            user.id
        )

        request.state.user_role = (
            user.role.value
        )

        if not role_can_access(
            user.role,
            request.method,
            path,
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "detail":
                        "You do not have permission "
                        "to access this StoreDash resource."
                },
            )

    finally:

        db.close()

    return await call_next(
        request
    )


app.add_middleware(
    CORSMiddleware,

    allow_origins=(
        settings.cors_origin_list
    ),

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(
        bind=engine
    )


app.include_router(
    health.router
)

app.include_router(
    auth.router,
    prefix="/api",
)

app.include_router(
    logistics.router,
    prefix="/api",
)

app.include_router(
    locations.router,
    prefix="/api",
)

app.include_router(
    users.router,
    prefix="/api",
)

app.include_router(
    businesses.router,
    prefix="/api",
)

app.include_router(
    business_suppliers.router,
    prefix="/api",
)

app.include_router(
    customer_insights.router,
    prefix="/api",
)

app.include_router(
    suppliers.router,
    prefix="/api",
)

app.include_router(
    drivers.router,
    prefix="/api",
)

app.include_router(
    driver_negotiation.router,
    prefix="/api",
)

app.include_router(
    driver_operations.router,
    prefix="/api",
)


app.include_router(
    delivery_market.router,
    prefix="/api",
)

app.include_router(
    orders.router,
    prefix="/api",
)

app.include_router(
    order_workflow.router,
    prefix="/api",
)

app.include_router(
    order_logistics.router,
    prefix="/api",
)

app.include_router(
    operating_days.router,
    prefix="/api",
)

app.include_router(batching.router, prefix="/api")
