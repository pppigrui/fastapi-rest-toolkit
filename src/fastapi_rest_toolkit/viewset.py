from typing import Any, Dict, Optional, Sequence, Type
from fastapi import HTTPException, status
from pydantic import BaseModel
from inspect import iscoroutinefunction
from .service import CRUDService
from .contextvar import ordering_parsed
from .filters import CRUDPlusFilterBackend, SearchFilterBackend, OrderingFilterBackend
from .permissions import BasePermission
from .throttle import BaseThrottle


class LimitOffsetPagination:
    default_limit = 20
    max_limit = 100

    def get(self, request) -> tuple[int, int]:
        qp = request.query_params or {}
        limit = int(qp.get("limit", self.default_limit))
        offset = int(qp.get("offset", 0))
        limit = max(1, min(limit, self.max_limit))
        offset = max(0, offset)
        return limit, offset

    def pack(self, *, total: int, results: list) -> dict:
        return {"count": total, "next": None, "previous": None, "results": results}


class ViewSet:
    service: CRUDService = None
    read_schema = None
    create_schema = None
    update_schema = None

    permission_classes: Sequence[Type[BasePermission]] = ()
    throttle_classes: Sequence[Type[BaseThrottle]] = ()
    filter_backends = (
        CRUDPlusFilterBackend(),
        SearchFilterBackend(),
        OrderingFilterBackend(),
    )
    pagination = LimitOffsetPagination()

    search_fields: Sequence[str] = ()
    ordering_fields: Sequence[str] = ()
    load_strategies: Optional[Sequence[str]] = None
    join_conditions: Optional[Any] = None
    throttle_scope: Optional[str] = None

    def get_permissions(self):
        return [
            permission if not isinstance(permission, type) else permission()
            for permission in self.permission_classes
        ]

    async def check_permissions(self, request):
        has_permission = False
        for p in self.get_permissions():
            if await p.has_permission(request, self):
                has_permission = True
                break
        if not has_permission and self.permission_classes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

    async def check_object_permissions(self, request, obj):
        for p in self.get_permissions():
            if not await p.has_object_permission(request, self, obj):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )

    def get_throttles(self):
        return [
            throttle if not isinstance(throttle, type) else throttle()
            for throttle in self.throttle_classes
        ]

    async def check_throttles(self, request):
        for throttle in self.get_throttles():
            func = throttle.allow_request
            if iscoroutinefunction(func):
                if not await func(request, self):
                    throttle.throttle_failure()
            else:
                if not func(request, self):
                    throttle.throttle_failure()

    def serialize(self, obj: Any):
        if self.read_schema is None:
            return obj

        if obj is None:
            return None

        if isinstance(obj, BaseModel):
            return obj.model_dump()

        if isinstance(obj, dict):
            return obj

        return self.read_schema.model_validate(obj).model_dump()

    def serialize_many(self, objs):
        return [self.serialize(x) for x in objs]

    def get_filters(self, request) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        for backend in self.filter_backends:
            filters = backend.apply(request=request, view=self, filters=filters)
        return filters

    async def list(self, request, session):
        await self.check_permissions(request)
        await self.check_throttles(request)
        filters = self.get_filters(request)
        limit, offset = self.pagination.get(request)
        ordering = ordering_parsed.get()

        total, items = await self.service.list(
            session,
            filters=filters,
            limit=limit,
            offset=offset,
            ordering=ordering,
            load_strategies=self.load_strategies,
            join_conditions=self.join_conditions,
        )
        return self.pagination.pack(total=total, results=self.serialize_many(items))

    async def _check(self, request):
        await self.check_permissions(request)
        await self.check_throttles(request)

    async def retrieve(self, request, session, pk: Any):
        await self._check(request)
        obj = await self.service.retrieve(
            session,
            pk=pk,
            load_strategies=self.load_strategies,
            join_conditions=self.join_conditions,
        )
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        await self.check_object_permissions(request, obj)
        return self.serialize(obj)

    async def create(self, request, session):
        await self._check(request)
        obj_in = self.create_schema(**(request.data or {}))
        obj = await self.service.create(session, obj_in=obj_in)
        return self.serialize(obj)

    async def update(self, request, session, pk: Any):
        await self._check(request)
        obj_in = self.update_schema(**(request.data or {}))
        await self.service.update(session, pk=pk, obj_in=obj_in)
        obj = await self.service.retrieve(session, pk=pk)
        return self.serialize(obj)

    async def partial_update(self, request, session, pk: Any):
        await self._check(request)
        obj_in = self.update_schema(**(request.data or {})).model_dump(
            exclude_unset=True
        )
        await self.service.update(session, pk=pk, obj_in=obj_in)
        obj = await self.service.retrieve(session, pk=pk)
        return self.serialize(obj)

    async def destroy(self, request, session, pk: Any):
        await self._check(request)
        obj = await self.service.retrieve(session, pk=pk)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        await self.check_object_permissions(request, obj)
        await self.service.destroy(session, pk=pk)
        return None
