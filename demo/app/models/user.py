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
from sqlalchemy.orm import relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class UserRole(str, Enum):
    MEMBER = "member"
    EDITOR = "editor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    name: Mapped[str] = mapped_column(String(50), info={"name": "姓名"})
    email: Mapped[str] = mapped_column(String(100), unique=True, info={"name": "邮箱"})
    phone: Mapped[str | None] = mapped_column(
        String(30), nullable=True, info={"name": "手机号"}
    )
    bio: Mapped[str | None] = mapped_column(
        Text, default="", nullable=True, info={"name": "个人简介"}
    )
    age: Mapped[int | None] = mapped_column(
        Integer, default=18, nullable=True, info={"name": "年龄"}
    )
    account_balance: Mapped[float | None] = mapped_column(
        Float, default=0.0, nullable=True, info={"name": "账户余额"}
    )
    birthday: Mapped[date | None] = mapped_column(
        Date, nullable=True, info={"name": "生日"}
    )
    role: Mapped[UserRole | None] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.MEMBER,
        nullable=True,
        info={"name": "角色"},
    )
    is_active: Mapped[bool] = mapped_column(default=True, info={"name": "是否激活"})
    is_staff: Mapped[bool] = mapped_column(
        Boolean, default=False, info={"name": "是否员工"}
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, info={"name": "最后登录时间"}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), info={"name": "创建时间"}
    )

    posts: Mapped[list["Post"]] = relationship(back_populates="author")
