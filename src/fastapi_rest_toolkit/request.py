from dataclasses import dataclass
from typing import Any, Mapping
from fastapi import Request


@dataclass
class FRFRequest:
    raw: Request
    user: Any = None
    data: Any = None
    query_params: Mapping[str, str] | None = None

    @classmethod
    async def from_fastapi(cls, request: Request, user: Any = None):
        data = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                data = await request.json()
            except Exception:
                data = None

        return cls(
            raw=request,
            user=user,
            data=data,
            query_params=dict(request.query_params),
        )
