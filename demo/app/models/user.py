from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    posts: Mapped[list["Post"]] = relationship(back_populates="author")
