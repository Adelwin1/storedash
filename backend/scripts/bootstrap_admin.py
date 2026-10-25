import sys

from sqlalchemy import select

from app.core.auth import (
    validate_email,
)

from app.core.db import (
    SessionLocal,
)

from app.models.entities import (
    ApprovedEmployee,
    Role,
)


if len(sys.argv) < 2:
    raise SystemExit(
        "Usage: python scripts/bootstrap_admin.py "
        "EMAIL [NAME]"
    )


email = validate_email(
    sys.argv[1]
)

name = (
    sys.argv[2]
    if len(sys.argv) > 2
    else "StoreDash Admin"
)


db = SessionLocal()

try:

    existing = db.scalar(
        select(
            ApprovedEmployee
        )
        .where(
            ApprovedEmployee.email
            ==
            email
        )
    )

    if existing is None:

        existing = ApprovedEmployee(
            email=email,
            name=name,
            role=Role.ADMIN,
            is_active=True,
        )

        db.add(
            existing
        )

    else:

        existing.name = name
        existing.role = Role.ADMIN
        existing.is_active = True

    db.commit()

    print(
        f"ADMIN EMAIL APPROVED: {email}"
    )

finally:

    db.close()
