from app.models import Role
from app.schemas.common import ORMModel
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    phone: str | None = None
    role: Role = Role.OPERATIONS


class UserRead(ORMModel):
    id: int
    name: str
    email: str
    phone: str | None
    role: Role
    is_active: bool
