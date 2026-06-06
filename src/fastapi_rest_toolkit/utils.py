from __future__ import annotations

from typing import Any, Literal, Optional, Type
from inspect import getmembers

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _optional(tp: Any) -> Any:
    return Optional[tp]


def _column_py_type(col: Column) -> Any:
    configured = col.info.get("python_type")
    if configured is not None:
        return configured

    # Most types have python_type
    try:
        return col.type.python_type
    except Exception:
        # Fallback: you can also extend more type mappings here
        return Any


def sqlalchemy_model_to_pydantic(
    sa_model: Type[DeclarativeBase],
    *,
    name: str | None = None,
    mode: Literal["read", "create", "update"] = "read",
    exclude: set[str] | None = None,
    overrides: dict[str, Any]
    | None = None,  # 用于强制某些字段类型，比如 email->EmailStr
) -> Type[BaseModel]:
    """
    mode:
      - read:   Includes all columns (except exclude), nullable->Optional; with from_attributes
      - create: Excludes auto-increment primary keys and server_default fields (e.g., created_at) by default, nullable->Optional
      - update: All fields Optional (for PATCH)
    """
    if mode not in {"read", "create", "update"}:
        raise ValueError("mode must be one of: read, create, update")

    exclude = exclude or set()
    overrides = overrides or {}

    fields: dict[str, tuple[Any, Any]] = {}

    for col in sa_model.__table__.columns:
        key = col.key
        if key in exclude:
            continue

        # create mode: typically don't need id / server_default fields
        if mode == "create":
            if col.primary_key and getattr(col, "autoincrement", False):
                continue
            if col.server_default is not None:
                continue

        py_type = overrides.get(key) or _column_py_type(col)

        # nullable fields -> Optional
        if col.nullable:
            py_type = _optional(py_type)

        default = ...
        # update mode: all Optional with default None
        if mode == "update":
            py_type = _optional(py_type)
            default = None
        else:
            # If there's a Python-side default, include it (server_default not handled here)
            if col.default is not None and getattr(col.default, "is_scalar", False):
                default = col.default.arg
            elif mode == "create" and col.nullable:
                default = None

        fields[key] = (py_type, default)

    model_name = name or f"{sa_model.__name__}{mode.capitalize()}Schema"

    # Enable ORM parsing for read mode
    if mode == "read":
        P = create_model(
            model_name,
            __base__=ORMBaseModel,
            **fields,
        )
    else:
        P = create_model(model_name, __base__=BaseModel, **fields)

    return P


def get_actions(viewset) -> dict[str, dict]:
    """
    Get metadata of all custom actions in ViewSet

    Returns:
        dict: {action_name: {"methods": tuple, "detail": bool, "url_path": str, "func": callable}}
    """
    actions = {}
    for name, method in getmembers(viewset):
        if getattr(method, "is_action", False):
            actions[name] = {
                "methods": method.action_methods,
                "detail": method.action_detail,
                "url_path": method.action_url_path,
                "func": method,
            }
    return actions
