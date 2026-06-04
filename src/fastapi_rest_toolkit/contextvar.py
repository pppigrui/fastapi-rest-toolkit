from contextvars import ContextVar
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

session_var: ContextVar[Optional[AsyncSession]] = ContextVar(
    "session_var", default=None
)
