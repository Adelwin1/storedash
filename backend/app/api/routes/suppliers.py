from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Supplier
from app.schemas.supplier import SupplierCreate, SupplierRead

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _number_match(q: str):
    """Translate supplier number 000 -> database id 1."""
    cleaned = q.strip()
    if cleaned.isdigit():
        return int(cleaned) + 1
    return None


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A supplier with this phone number already exists.")
    db.refresh(supplier)
    return supplier


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    q: str | None = Query(default=None, description="Search by supplier number, name, phone, contact or category"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Supplier).order_by(Supplier.name).limit(limit)
    if q:
        cleaned = q.strip()
        pattern = f"%{cleaned}%"
        supplier_id = _number_match(cleaned)
        conditions = [
            Supplier.name.ilike(pattern),
            Supplier.phone.ilike(pattern),
            Supplier.contact_person.ilike(pattern),
            Supplier.category.ilike(pattern),
        ]
        if supplier_id is not None:
            conditions.append(Supplier.id == supplier_id)
        stmt = select(Supplier).where(or_(*conditions)).order_by(Supplier.name).limit(limit)
    return db.scalars(stmt).all()


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


from pydantic import BaseModel, Field


class SupplierLocationUpdate(BaseModel):
    location: str

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


@router.patch(
    "/{supplier_id}/location",
)
def update_supplier_location(
    supplier_id: int,
    payload: SupplierLocationUpdate,
    db: Session = Depends(get_db),
):
    supplier = db.get(
        Supplier,
        supplier_id,
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    supplier.location = (
        payload.location.strip()
    )

    supplier.latitude = (
        payload.latitude
    )

    supplier.longitude = (
        payload.longitude
    )

    db.commit()
    db.refresh(supplier)

    return {
        "id": supplier.id,
        "location": supplier.location,
        "latitude": supplier.latitude,
        "longitude": supplier.longitude,
    }
