from contextvars import ContextVar
from typing import Tuple

ordering_parsed: ContextVar[Tuple[list, list]] = ContextVar(
    "ordering_parsed", default=([], [])
)
