from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    clear_session_cookie,
    create_session,
    current_user_id,
    hash_password,
    normalize_email,
    set_session_cookie,
    token_digest,
    validate_email,
    verify_password,
)

from app.core.db import get_db

from app.models.entities import (
    ApprovedEmployee,
    AuthSession,
    Role,
    User,
    UserCredential,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class SignupRequest(
    BaseModel
):
    name: str = Field(
        min_length=1,
        max_length=120,
    )

    email: str

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    password: str = Field(
        min_length=10,
        max_length=200,
    )


class LoginRequest(
    BaseModel
):
    email: str

    password: str = Field(
        min_length=1,
        max_length=200,
    )


class ApproveEmployeeRequest(
    BaseModel
):
    email: str

    name: str | None = Field(
        default=None,
        max_length=120,
    )

    role: Role = Role.OPERATIONS


def serialize_user(
    user: User,
):
    return {
        "id":
            user.id,

        "name":
            user.name,

        "email":
            user.email,

        "phone":
            user.phone,

        "role":
            user.role.value,

        "is_active":
            user.is_active,
    }


def require_admin(
    request: Request,
    db: Session,
):

    user_id = current_user_id(
        request
    )

    user = db.get(
        User,
        user_id,
    )

    if (
        user is None
        or user.role != Role.ADMIN
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    return user


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
):

    email = validate_email(
        payload.email
    )

    approved = db.scalar(
        select(
            ApprovedEmployee
        )
        .where(
            ApprovedEmployee.email
            ==
            email,
            ApprovedEmployee.is_active.is_(
                True
            ),
        )
    )

    if approved is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "This email is not authorized "
                "to create a StoreDash account."
            ),
        )

    if approved.claimed_user_id is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "An account has already been "
                "created for this email."
            ),
        )

    existing = db.scalar(
        select(
            User
        )
        .where(
            User.email
            ==
            email
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "An account already exists "
                "for this email."
            ),
        )

    (
        salt,
        password_hash,
        iterations,
    ) = hash_password(
        payload.password
    )

    user = User(
        name=payload.name.strip(),
        email=email,
        phone=(
            payload.phone.strip()
            if payload.phone
            else None
        ),
        role=approved.role,
        is_active=True,
    )

    db.add(
        user
    )

    db.flush()

    credential = UserCredential(
        user_id=user.id,
        password_salt=salt,
        password_hash=password_hash,
        password_iterations=iterations,
    )

    db.add(
        credential
    )

    approved.claimed_user_id = (
        user.id
    )

    approved.claimed_at = (
        datetime.utcnow()
    )

    db.commit()

    db.refresh(
        user
    )

    (
        token,
        _,
    ) = create_session(
        db,
        user.id,
    )

    set_session_cookie(
        response,
        token,
    )

    return serialize_user(
        user
    )


@router.post(
    "/login"
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(
            User
        )
        .where(
            User.email
            ==
            email
        )
    )

    if (
        user is None
        or not user.is_active
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    credential = db.scalar(
        select(
            UserCredential
        )
        .where(
            UserCredential.user_id
            ==
            user.id
        )
    )

    if (
        credential is None
        or not verify_password(
            payload.password,
            credential,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    (
        token,
        _,
    ) = create_session(
        db,
        user.id,
    )

    set_session_cookie(
        response,
        token,
    )

    return serialize_user(
        user
    )


@router.post(
    "/logout"
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    raw_token = request.cookies.get(
        "storedash_session"
    )

    if raw_token:
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
            )
        )

        if session is not None:
            session.revoked_at = (
                datetime.utcnow()
            )

            db.commit()

    clear_session_cookie(
        response
    )

    return {
        "ok": True
    }


@router.get(
    "/me"
)
def me(
    request: Request,
    db: Session = Depends(get_db),
):

    user_id = current_user_id(
        request
    )

    user = db.get(
        User,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return serialize_user(
        user
    )


@router.get(
    "/approved-employees"
)
def list_approved_employees(
    request: Request,
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    rows = list(
        db.scalars(
            select(
                ApprovedEmployee
            )
            .order_by(
                ApprovedEmployee.email
            )
        ).all()
    )

    return [
        {
            "id":
                row.id,

            "email":
                row.email,

            "name":
                row.name,

            "role":
                row.role.value,

            "is_active":
                row.is_active,

            "claimed_user_id":
                row.claimed_user_id,
        }
        for row in rows
    ]


@router.post(
    "/approved-employees",
    status_code=status.HTTP_201_CREATED,
)
def approve_employee(
    payload: ApproveEmployeeRequest,
    request: Request,
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    email = validate_email(
        payload.email
    )

    row = db.scalar(
        select(
            ApprovedEmployee
        )
        .where(
            ApprovedEmployee.email
            ==
            email
        )
    )

    if row is None:

        row = ApprovedEmployee(
            email=email,
            name=payload.name,
            role=payload.role,
            is_active=True,
        )

        db.add(
            row
        )

    else:

        row.name = (
            payload.name
            or row.name
        )

        row.role = (
            payload.role
        )

        row.is_active = True

    db.commit()

    db.refresh(
        row
    )

    return {
        "id":
            row.id,

        "email":
            row.email,

        "name":
            row.name,

        "role":
            row.role.value,

        "is_active":
            row.is_active,

        "claimed_user_id":
            row.claimed_user_id,
    }


@router.post(
    "/approved-employees/{approved_id}/deactivate"
)
def deactivate_employee(
    approved_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    row = db.get(
        ApprovedEmployee,
        approved_id,
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Approved employee not found.",
        )

    row.is_active = False

    if row.claimed_user_id is not None:

        user = db.get(
            User,
            row.claimed_user_id,
        )

        if user is not None:
            user.is_active = False

        sessions = list(
            db.scalars(
                select(
                    AuthSession
                )
                .where(
                    AuthSession.user_id
                    ==
                    row.claimed_user_id,
                    AuthSession.revoked_at.is_(
                        None
                    ),
                )
            ).all()
        )

        for session in sessions:
            session.revoked_at = (
                datetime.utcnow()
            )

    db.commit()

    return {
        "ok": True
    }
