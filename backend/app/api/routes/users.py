from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=status.HTTP_403_FORBIDDEN)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=403,
        detail=(
            "Direct employee creation is disabled. "
            "Use the approved StoreDash signup flow."
        ),
    )


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.name)).all()
