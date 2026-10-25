import hashlib
import hmac
import os
import secrets

from datetime import (
    datetime,
    timedelta,
)

from fastapi import (
    HTTPException,
    Request,
    status,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuthSession,
    User,
    UserCredential,
)


SESSION_COOKIE_NAME = "storedash_session"
SESSION_DAYS = 30
PASSWORD_ITERATIONS = 310000


def normalize_email(
    email: str,
) -> str:

    return email.strip().lower()


def validate_email(
    email: str,
) -> str:

    email = normalize_email(
        email
    )

    if (
        not email
        or "@" not in email
        or "." not in email.split("@")[-1]
    ):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid email address.",
        )

    return email


def hash_password(
    password: str,
    salt_hex: str | None = None,
    iterations: int = PASSWORD_ITERATIONS,
):

    if len(password) < 10:
        raise HTTPException(
            status_code=422,
            detail=(
                "Password must be at least "
                "10 characters."
            ),
        )

    if salt_hex is None:
        salt = secrets.token_bytes(
            32
        )

        salt_hex = salt.hex()

    else:
        salt = bytes.fromhex(
            salt_hex
        )

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return (
        salt_hex,
        digest.hex(),
        iterations,
    )


def verify_password(
    password: str,
    credential: UserCredential,
) -> bool:

    try:
        (
            _,
            candidate,
            _,
        ) = hash_password(
            password,
            credential.password_salt,
            credential.password_iterations,
        )

    except Exception:
        return False

    return hmac.compare_digest(
        candidate,
        credential.password_hash,
    )


def token_digest(
    token: str,
) -> str:

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_session(
    db: Session,
    user_id: int,
):

    raw_token = secrets.token_urlsafe(
        48
    )

    expires_at = (
        datetime.utcnow()
        +
        timedelta(
            days=SESSION_DAYS
        )
    )

    session = AuthSession(
        user_id=user_id,
        token_hash=token_digest(
            raw_token
        ),
        expires_at=expires_at,
    )

    db.add(
        session
    )

    db.commit()

    return (
        raw_token,
        expires_at,
    )


def get_user_from_token(
    db: Session,
    raw_token: str | None,
):

    if not raw_token:
        return None

    session = db.scalar(
        select(
            AuthSession
        )
        .where(
            AuthSession.token_hash
            ==
            token_digest(
                raw_token
            ),
            AuthSession.revoked_at.is_(
                None
            ),
            AuthSession.expires_at
            >
            datetime.utcnow(),
        )
    )

    if session is None:
        return None

    user = db.get(
        User,
        session.user_id,
    )

    if (
        user is None
        or not user.is_active
    ):
        return None

    return user


def authenticate_request(
    request: Request,
    db: Session,
):

    raw_token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    return get_user_from_token(
        db,
        raw_token,
    )


def current_user_id(
    request: Request,
) -> int:

    user_id = getattr(
        request.state,
        "user_id",
        None,
    )

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return int(
        user_id
    )


def cookie_secure() -> bool:

    return (
        os.getenv(
            "AUTH_COOKIE_SECURE",
            "false",
        )
        .strip()
        .lower()
        ==
        "true"
    )


def set_session_cookie(
    response,
    token: str,
):

    secure = cookie_secure()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=(
            SESSION_DAYS
            *
            24
            *
            60
            *
            60
        ),
        httponly=True,
        secure=secure,
        samesite=(
            "none"
            if secure
            else
            "lax"
        ),
        path="/",
    )


def clear_session_cookie(
    response,
):

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )
