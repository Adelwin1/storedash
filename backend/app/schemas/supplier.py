from datetime import datetime

from app.schemas.common import ORMModel
from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str | None = None
    phone: str = Field(min_length=5, max_length=30)
    contact_person: str | None = None
    location: str | None = None
    landmark: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pickup_notes: str | None = None
    willing_to_fulfill: bool = True
    created_by_id: int | None = None


class SupplierRead(ORMModel):
    id: int
    supplier_number: str
    name: str
    category: str | None
    phone: str
    contact_person: str | None
    location: str | None
    landmark: str | None
    latitude: float | None
    longitude: float | None
    pickup_notes: str | None
    willing_to_fulfill: bool
    created_at: datetime
