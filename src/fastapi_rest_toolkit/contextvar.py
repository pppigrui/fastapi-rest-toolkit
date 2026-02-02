from contextvars import ContextVar
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession

ordering_parsed: ContextVar[Tuple[list, list]] = ContextVar(
    "ordering_parsed", default=([], [])
)

session_var: ContextVar[AsyncSession] = ContextVar(
    "session_var", default=None
)
