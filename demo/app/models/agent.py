from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    code: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, info={"name": "编码"}
    )
    name: Mapped[str] = mapped_column(String(100), info={"name": "名称"})
    setting: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, info={"name": "记忆设置"}
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, info={"name": "描述"}
    )
    prompt: Mapped[str] = mapped_column(Text, info={"name": "提示词"})
    tools: Mapped[list[Any] | None] = mapped_column(
        JSON, nullable=True, info={"name": "工具列表", "python_type": list}
    )
    model: Mapped[str] = mapped_column(String(100), info={"name": "模型"})
    parameters: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, info={"name": "模型参数"}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), info={"name": "创建时间"}
    )
