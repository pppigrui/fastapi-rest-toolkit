class BasePermission:
    async def has_permission(self, request, view) -> bool:
        return True

    async def has_object_permission(self, request, view, obj) -> bool:
        return True


class AllowAny(BasePermission):
    async def has_permission(self, request, view) -> bool:
        return True


class IsAuthenticated(BasePermission):
    async def has_permission(self, request, view) -> bool:
        return request.user is not None


class IsAdmin(BasePermission):
    async def has_permission(self, request, view) -> bool:
        return bool(getattr(request.user, "is_admin", False))
