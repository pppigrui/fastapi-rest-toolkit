from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLAlchemyEnum,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class PostStatus(str, Enum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    title: Mapped[str] = mapped_column(String(200), info={"name": "标题"})
    summary: Mapped[str | None] = mapped_column(
        Text, default="", nullable=True, info={"name": "摘要"}
    )
    content: Mapped[str] = mapped_column(String(1000), info={"name": "内容"})
    category: Mapped[str | None] = mapped_column(
        String(30), default="tech", nullable=True, info={"name": "分类"}
    )
    status: Mapped[PostStatus | None] = mapped_column(
        SQLAlchemyEnum(
            PostStatus,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=PostStatus.DRAFT,
        nullable=True,
        info={"name": "状态"},
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, info={"name": "是否发布"}
    )
    view_count: Mapped[int | None] = mapped_column(
        Integer, default=0, nullable=True, info={"name": "浏览量"}
    )
    rating: Mapped[float | None] = mapped_column(
        Float, default=0.0, nullable=True, info={"name": "评分"}
    )
    priority: Mapped[int | None] = mapped_column(
        Integer, default=0, nullable=True, info={"name": "优先级"}
    )
    publish_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, info={"name": "发布日期"}
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, info={"name": "发布时间"}
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), info={"name": "作者ID"}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), info={"name": "创建时间"}
    )

    author: Mapped["User"] = relationship(back_populates="posts")
