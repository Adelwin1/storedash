from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class BusinessCreate(BaseModel):
    owner_name: str = Field(min_length=1, max_length=120)
    business_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=5, max_length=30)
    alternate_phone: str | None = None
    business_type: str | None = None
    address: str | None = None
    landmark: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    delivery_instructions: str | None = None
    created_by_id: int | None = None


class BusinessRead(ORMModel):
    id: int
    customer_number: str
    owner_name: str
    business_name: str
    phone: str
    alternate_phone: str | None
    business_type: str | None
    address: str | None
    landmark: str | None
    latitude: float | None
    longitude: float | None
    delivery_instructions: str | None
    created_at: datetime
