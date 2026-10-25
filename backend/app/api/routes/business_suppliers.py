from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import (
    Business,
    BusinessSupplier,
    Supplier,
)


router = APIRouter(
    prefix="/businesses",
    tags=["business-suppliers"],
)


class PairedSupplierRead(BaseModel):
    relationship_id: int

    supplier_id: int
    supplier_number: str

    name: str

    category: str | None = None
    phone: str

    contact_person: str | None = None
    location: str | None = None

    is_usual: bool

    notes: str | None = None


def serialize_pair(
    pair: BusinessSupplier,
    supplier: Supplier,
):
    return {
        "relationship_id":
            pair.id,

        "supplier_id":
            supplier.id,

        "supplier_number":
            supplier.supplier_number,

        "name":
            supplier.name,

        "category":
            supplier.category,

        "phone":
            supplier.phone,

        "contact_person":
            supplier.contact_person,

        "location":
            supplier.location,

        "is_usual":
            pair.is_usual,

        "notes":
            pair.notes,
    }


@router.get(
    "/{business_id}/suppliers",
    response_model=list[
        PairedSupplierRead
    ],
)
def list_business_suppliers(
    business_id: int,
    db: Session = Depends(get_db),
):
    business = db.get(
        Business,
        business_id,
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )


    rows = db.execute(
        select(
            BusinessSupplier,
            Supplier,
        )
        .join(
            Supplier,
            Supplier.id
            == BusinessSupplier.supplier_id,
        )
        .where(
            BusinessSupplier.business_id
            == business_id
        )
        .order_by(
            Supplier.name
        )
    ).all()


    return [
        serialize_pair(
            pair,
            supplier,
        )
        for pair, supplier
        in rows
    ]


@router.post(
    "/{business_id}/suppliers/{supplier_id}",
    response_model=PairedSupplierRead,
    status_code=status.HTTP_201_CREATED,
)
def pair_supplier(
    business_id: int,
    supplier_id: int,
    db: Session = Depends(get_db),
):
    business = db.get(
        Business,
        business_id,
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )


    supplier = db.get(
        Supplier,
        supplier_id,
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found.",
        )


    existing = db.scalars(
        select(
            BusinessSupplier
        ).where(
            BusinessSupplier.business_id
            == business_id,

            BusinessSupplier.supplier_id
            == supplier_id,
        )
    ).first()


    if existing:
        return serialize_pair(
            existing,
            supplier,
        )


    pair = BusinessSupplier(
        business_id=business_id,
        supplier_id=supplier_id,
        is_usual=True,
    )


    db.add(pair)

    db.commit()

    db.refresh(pair)


    return serialize_pair(
        pair,
        supplier,
    )


@router.delete(
    "/{business_id}/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_supplier_pair(
    business_id: int,
    supplier_id: int,
    db: Session = Depends(get_db),
):
    pair = db.scalars(
        select(
            BusinessSupplier
        ).where(
            BusinessSupplier.business_id
            == business_id,

            BusinessSupplier.supplier_id
            == supplier_id,
        )
    ).first()


    if not pair:
        raise HTTPException(
            status_code=404,
            detail=(
                "This supplier is not paired "
                "with this customer."
            ),
        )


    db.delete(pair)

    db.commit()

    return None
