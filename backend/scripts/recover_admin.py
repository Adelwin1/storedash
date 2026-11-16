from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.core.auth import validate_email
from app.core.db import SessionLocal
from app.models.entities import (
    ApprovedEmployee,
    Role,
    User,
)


def main():
    raw_email = input(
        "Admin email to restore/create: "
    ).strip()

    email = validate_email(
        raw_email
    )

    db = SessionLocal()

    try:
        user = db.scalar(
            select(User)
            .where(
                User.email == email
            )
        )

        approval = db.scalar(
            select(
                ApprovedEmployee
            )
            .where(
                ApprovedEmployee.email
                ==
                email
            )
        )

        if approval is None:
            approval = (
                ApprovedEmployee(
                    email=email,
                    name=(
                        user.name
                        if user is not None
                        else None
                    ),
                    role=Role.ADMIN,
                    is_active=True,
                )
            )

            db.add(
                approval
            )

        approval.role = (
            Role.ADMIN
        )

        approval.is_active = (
            True
        )

        if user is not None:
            user.role = (
                Role.ADMIN
            )

            user.is_active = (
                True
            )

            approval.claimed_user_id = (
                user.id
            )

            if (
                approval.claimed_at
                is None
            ):
                approval.claimed_at = (
                    datetime.utcnow()
                )

        db.commit()

        if user is not None:
            print(
                f"Admin restored: {email}"
            )
            print(
                "Existing StoreDash account "
                "reactivated and promoted to admin."
            )

        else:
            print(
                f"Admin email approved: {email}"
            )
            print(
                "No StoreDash account exists yet. "
                "Create the account from /signup "
                "using this exact email."
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()
