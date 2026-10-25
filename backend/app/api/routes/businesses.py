from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Business
from app.schemas.business import BusinessCreate, BusinessRead

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _number_match(q: str):
    """Translate customer number 000 -> database id 1."""
    cleaned = q.strip()
    if cleaned.isdigit():
        return int(cleaned) + 1
    return None


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, db: Session = Depends(get_db)):
    business = Business(**payload.model_dump())
    db.add(business)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A customer with this phone number already exists.")
    db.refresh(business)
    return business


@router.get("", response_model=list[BusinessRead])
def list_businesses(
    q: str | None = Query(default=None, description="Search by customer number, owner, business name, or phone"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Business).order_by(Business.created_at.desc()).limit(limit)
    if q:
        cleaned = q.strip()
        pattern = f"%{cleaned}%"
        customer_id = _number_match(cleaned)
        conditions = [
            Business.owner_name.ilike(pattern),
            Business.business_name.ilike(pattern),
            Business.phone.ilike(pattern),
        ]
        if customer_id is not None:
            conditions.append(Business.id == customer_id)
        stmt = (
            select(Business)
            .where(or_(*conditions))
            .order_by(Business.created_at.desc())
            .limit(limit)
        )
    return db.scalars(stmt).all()


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(business_id: int, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Customer not found")
    return business


from pydantic import BaseModel, Field


class BusinessLocationUpdate(BaseModel):
    address: str

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


@router.patch(
    "/{business_id}/location",
)
def update_business_location(
    business_id: int,
    payload: BusinessLocationUpdate,
    db: Session = Depends(get_db),
):
    business = db.get(
        Business,
        business_id,
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    business.address = (
        payload.address.strip()
    )

    business.latitude = (
        payload.latitude
    )

    business.longitude = (
        payload.longitude
    )

    db.commit()
    db.refresh(business)

    return {
        "id": business.id,
        "address": business.address,
        "latitude": business.latitude,
        "longitude": business.longitude,
    }
