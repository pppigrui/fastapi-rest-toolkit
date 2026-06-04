from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .viewset import ViewSet
    from .request import FRFRequest


class BasePermission:
    async def has_permission(self, request: "FRFRequest", view: "ViewSet") -> bool:
        return True

    async def has_object_permission(
        self, request: "FRFRequest", view: "ViewSet", obj: Any
    ) -> bool:
        return True


class AllowAny(BasePermission):
    async def has_permission(self, request: "FRFRequest", view: "ViewSet") -> bool:
        return True


class IsAuthenticated(BasePermission):
    async def has_permission(self, request: "FRFRequest", view: "ViewSet") -> bool:
        return request.user is not None


class IsAdmin(BasePermission):
    async def has_permission(self, request: "FRFRequest", view: "ViewSet") -> bool:
        return bool(getattr(request.user, "is_admin", False))
