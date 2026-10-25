from pydantic import (
    BaseModel,
    Field,
)

from app.schemas.common import ORMModel


class DriverCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
    )

    phone: str = Field(
        min_length=5,
        max_length=30,
    )

    vehicle_type: str = "tricycle"

    vehicle_registration: str | None = None

    current_area: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    payment_phone: str | None = None
    payment_name: str | None = None

    notes: str | None = None

    is_available: bool = True
    is_active: bool = True


class DriverUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None

    vehicle_type: str | None = None
    vehicle_registration: str | None = None

    current_area: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    payment_phone: str | None = None
    payment_name: str | None = None

    notes: str | None = None

    is_available: bool | None = None
    is_active: bool | None = None


class DriverRead(ORMModel):
    id: int

    name: str
    phone: str

    vehicle_type: str
    vehicle_registration: str | None = None

    current_area: str | None

    latitude: float | None = None
    longitude: float | None = None

    payment_phone: str | None = None
    payment_name: str | None = None

    notes: str | None = None

    is_available: bool
    is_active: bool

    completion_rate: float
