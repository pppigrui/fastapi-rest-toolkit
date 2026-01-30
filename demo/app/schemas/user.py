from pydantic import EmailStr
from app.schemas import BaseSchema


class UserRead(BaseSchema):
    id: int
    email: EmailStr
    name: str
    is_active: bool

class UserCreate(BaseSchema):
    email: EmailStr
    name: str
    is_active: bool = False


class UserUpdate(BaseSchema):
    email: EmailStr | None = None
    name: str | None = None
    is_active: bool | None = None
