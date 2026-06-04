from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .request import FRFRequest


class BaseAuthentication(ABC):
    @abstractmethod
    async def authenticate(self, request: "FRFRequest") -> tuple[Any, Any]:
        pass


class BearerAuthentication(BaseAuthentication):
    def get_token(
        self, request: "FRFRequest", start_with: str = "bearer "
    ) -> Optional[str]:
        authorization = request.raw.headers.get("authorization")
        if not authorization or not authorization.lower().startswith(start_with):
            return None
        _, _, token = authorization.partition(" ")
        token = token.strip()
        return token or None

    async def authenticate(self, request: "FRFRequest") -> tuple[Any, Any]:
        token = self.get_token(request, start_with="bearer ")
        user = None
        if token is None:
            return None, None
        return user, token
