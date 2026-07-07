from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    name: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, info={"name": "标签名"}
    )
    color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, info={"name": "颜色"}
    )


class PostTag(Base):
    __tablename__ = "post_tags"
    __table_args__ = (
        UniqueConstraint("post_id", "tag_id", name="uq_post_tags_post_tag"),
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
        info={"name": "文章 ID"},
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        info={"name": "标签 ID"},
    )
