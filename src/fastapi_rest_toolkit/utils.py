from __future__ import annotations

from typing import Any, Optional, Type

from pydantic import BaseModel, create_model
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase


def _optional(tp: Any) -> Any:
    return Optional[tp]


def _column_py_type(col: Column) -> Any:
    # 大多数类型都有 python_type
    try:
        return col.type.python_type
    except Exception:
        # 兜底：你也可以在这里扩展更多类型映射
        return Any


def sqlalchemy_model_to_pydantic(
    sa_model: Type[DeclarativeBase],
    *,
    name: str | None = None,
    mode: str = "read",  # "read" | "create" | "update"
    exclude: set[str] | None = None,
    overrides: dict[str, Any] | None = None,  # 用于强制某些字段类型，比如 email->EmailStr
) -> Type[BaseModel]:
    """
    mode:
      - read:   包含所有列（除 exclude），nullable->Optional；带 from_attributes
      - create: 默认排除自增主键、server_default字段（比如 created_at），nullable->Optional
      - update: 全部字段 Optional（用于 PATCH）
    """
    exclude = exclude or set()
    overrides = overrides or {}

    fields: dict[str, tuple[Any, Any]] = {}

    for col in sa_model.__table__.columns:
        key = col.key
        if key in exclude:
            continue

        # create 模式：通常不需要 id / server_default 字段
        if mode == "create":
            if col.primary_key and getattr(col, "autoincrement", False):
                continue
            if col.server_default is not None:
                continue

        py_type = overrides.get(key) or _column_py_type(col)

        # 可空字段 -> Optional
        if col.nullable:
            py_type = _optional(py_type)

        default = ...
        # update 模式：全部 Optional 且默认 None
        if mode == "update":
            py_type = _optional(py_type)
            default = None
        else:
            # 有 Python-side default 的话可以带上（server_default 不在这里处理）
            if col.default is not None and getattr(col.default, "is_scalar", False):
                default = col.default.arg

        fields[key] = (py_type, default)

    model_name = name or f"{sa_model.__name__}{mode.capitalize()}Schema"

    # read 模式启用 ORM 解析
    if mode == "read":
        P = create_model(
            model_name,
            __base__=BaseModel,
            __config__={"from_attributes": True},
            **fields,
        )
    else:
        P = create_model(model_name, __base__=BaseModel, **fields)

    return P
