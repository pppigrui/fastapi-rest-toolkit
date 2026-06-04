from typing import Any, Dict, Optional, Sequence, Type
from fastapi import HTTPException, status
from pydantic import BaseModel
from inspect import iscoroutinefunction

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .service import CRUDService
from .contextvar import session_var
from .filters import CRUDPlusFilterBackend, SearchFilterBackend, OrderingFilterBackend
from .permissions import BasePermission
from .throttle import BaseThrottle
from .authentication import BaseAuthentication
from .request import FRFRequest
from .utils import sqlalchemy_model_to_pydantic


class LimitOffsetPagination:
    default_limit = 20
    max_limit = 100

    def get(self, request: FRFRequest) -> tuple[int, int]:
        qp = request.query_params or {}
        try:
            limit = int(qp.get("limit", self.default_limit))
            offset = int(qp.get("offset", 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="limit and offset must be integers",
            ) from exc
        limit = max(1, min(limit, self.max_limit))
        offset = max(0, offset)
        return limit, offset

    def pack(self, *, total: int, results: list) -> dict:
        return {"count": total, "next": None, "previous": None, "results": results}


class ViewSet:
    model: Type[DeclarativeBase] = None
    service: CRUDService = None
    read_schema: Type[BaseModel] = None
    create_schema: Type[BaseModel] = None
    update_schema: Type[BaseModel] = None

    permission_classes: Sequence[Type[BasePermission] | BasePermission] = ()
    throttle_classes: Sequence[Type[BaseThrottle] | BaseThrottle] = ()
    authentication_classes: Sequence[Type[BaseAuthentication] | BaseAuthentication] = ()
    filter_backends = (
        CRUDPlusFilterBackend(),
        SearchFilterBackend(),
        OrderingFilterBackend(),
    )
    pagination = LimitOffsetPagination()

    search_fields: Sequence[str] = ()  # Searchable fields
    ordering_fields: Sequence[str] = ()  # Orderable fields
    load_strategies: Optional[Sequence[str]] = None
    join_conditions: Optional[Any] = None
    throttle_scope: Optional[str] = None

    allowed_actions = ("list", "retrieve", "create", "update", "destroy")

    def validate_configuration(self):
        service_actions = {"list", "retrieve", "create", "update", "destroy"}
        enabled_service_actions = service_actions.intersection(self.allowed_actions)
        if enabled_service_actions and self.service is None:
            raise RuntimeError("ViewSet.service must be configured for CRUD actions")
        if "create" in self.allowed_actions and self.create_schema is None:
            raise RuntimeError("ViewSet.create_schema must be configured for create")
        if "update" in self.allowed_actions and self.update_schema is None:
            raise RuntimeError("ViewSet.update_schema must be configured for update")

    def get_authentications(self) -> list[BaseAuthentication]:
        return [
            authentication if not isinstance(authentication, type) else authentication()
            for authentication in self.authentication_classes
        ]

    def get_permissions(self) -> list[BasePermission]:
        return [
            permission if not isinstance(permission, type) else permission()
            for permission in self.permission_classes
        ]

    def get_throttles(self) -> list[BaseThrottle]:
        throttles = []
        for throttle in self.throttle_classes:
            if not isinstance(throttle, type):
                throttles.append(throttle)
                continue
            try:
                throttles.append(throttle())
            except TypeError as exc:
                raise RuntimeError(
                    "Throttle classes must be instantiable without arguments. "
                    "Pass a throttle instance when dependencies are required."
                ) from exc
        return throttles

    async def check_authentications(self, request: FRFRequest):
        authenticated = False
        for authentication in self.get_authentications():
            user, _ = await authentication.authenticate(request)
            if user is None:
                continue
            request.user = user
            authenticated = True
            break
        if not authenticated and self.authentication_classes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )

    async def check_permissions(self, request: FRFRequest):
        for p in self.get_permissions():
            if not await p.has_permission(request, self):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )

    async def check_object_permissions(self, request: FRFRequest, obj: Any):
        for p in self.get_permissions():
            if not await p.has_object_permission(request, self, obj):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )

    async def check_throttles(self, request: FRFRequest):
        for throttle in self.get_throttles():
            func = throttle.allow_request
            if iscoroutinefunction(func):
                if not await func(request, self):
                    throttle.throttle_failure()
            else:
                if not func(request, self):
                    throttle.throttle_failure()

    def serialize(self, obj: Any) -> dict | BaseModel | None:
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

    def get_filters(self, request: FRFRequest) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        for backend in self.filter_backends:
            filters = backend.apply(request=request, view=self, filters=filters)
        return filters

    async def _check(self, request: FRFRequest, *, session: AsyncSession):
        session_var.set(session)
        await self.check_authentications(request)
        await self.check_permissions(request)
        await self.check_throttles(request)

    async def list(self, request: FRFRequest, session: AsyncSession):
        await self._check(request, session=session)
        filters = self.get_filters(request)
        limit, offset = self.pagination.get(request)
        ordering = request.ordering

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

    async def retrieve(self, request: FRFRequest, session: AsyncSession, pk: Any):
        await self._check(request, session=session)
        obj = await self.service.retrieve(
            session,
            pk=pk,
            load_strategies=self.load_strategies,
            join_conditions=self.join_conditions,
        )
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        await self.check_object_permissions(request, obj)
        return self.serialize(obj)

    async def create(self, request: FRFRequest, session: AsyncSession):
        await self._check(request, session=session)
        obj_in = self.create_schema(**(request.data or {}))
        obj = await self.service.create(session, obj_in=obj_in)
        return self.serialize(obj)

    async def update(self, request: FRFRequest, session: AsyncSession, pk: Any):
        await self._check(request, session=session)
        obj = await self.service.retrieve(
            session,
            pk=pk,
            load_strategies=self.load_strategies,
            join_conditions=self.join_conditions,
        )
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        await self.check_object_permissions(request, obj)
        obj_in = self.update_schema(**(request.data or {}))
        await self.service.update(session, pk=pk, obj_in=obj_in)
        obj = await self.service.retrieve(
            session,
            pk=pk,
            load_strategies=self.load_strategies,
            join_conditions=self.join_conditions,
        )
        return self.serialize(obj)

    async def destroy(self, request: FRFRequest, session: AsyncSession, pk: Any):
        await self._check(request, session=session)
        obj = await self.service.retrieve(session, pk=pk)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
            )
        await self.check_object_permissions(request, obj)
        await self.service.destroy(session, pk=pk)
        return None

    def init_schema(self):
        if self.model is None or not issubclass(self.model, DeclarativeBase):
            return
        if all(
            [
                "list" in self.allowed_actions
                or "retrieve" in self.allowed_actions
                or "destroy" in self.allowed_actions,
                self.read_schema is None,
            ]
        ):
            self.read_schema = sqlalchemy_model_to_pydantic(
                self.model, name=f"{self.model.__name__}Read"
            )

        if all(
            [
                "create" in self.allowed_actions,
                self.create_schema is None,
            ]
        ):
            self.create_schema = sqlalchemy_model_to_pydantic(
                self.model, name=f"{self.model.__name__}Create", mode="create"
            )
        if all(
            [
                "update" in self.allowed_actions,
                self.update_schema is None,
            ]
        ):
            self.update_schema = sqlalchemy_model_to_pydantic(
                self.model, name=f"{self.model.__name__}Update", mode="update"
            )
