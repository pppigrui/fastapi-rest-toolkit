import json
from dataclasses import dataclass
from typing import Any, Mapping
from fastapi import HTTPException, Request, status


@dataclass
class FRFRequest:
    raw: Request
    user: Any = None
    data: Any = None
    query_params: Mapping[str, str] | None = None
    ordering: tuple[list[str], list[str]] | None = None

    @classmethod
    async def from_fastapi(cls, request: Request):
        data = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if body:
                try:
                    data = json.loads(body)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Malformed JSON body",
                    ) from exc

        return cls(
            raw=request,
            data=data,
            query_params=dict(request.query_params),
        )
