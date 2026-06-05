from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    title: Mapped[str] = mapped_column(String(200), info={"name": "标题"})
    content: Mapped[str] = mapped_column(String(1000), info={"name": "内容"})
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), info={"name": "作者ID"}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), info={"name": "创建时间"}
    )

    author: Mapped["User"] = relationship(back_populates="posts")
