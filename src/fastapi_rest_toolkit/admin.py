from __future__ import annotations

from dataclasses import dataclass
from html import escape
from importlib import resources
from pathlib import PurePosixPath
from typing import Any, Callable, Sequence, Type

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy_crud_plus import CRUDPlus

from .authentication import BaseAuthentication
from .filters import OrderingFilterBackend, SearchFilterBackend
from .permissions import BasePermission
from .router import DefaultRouter
from .service import CRUDService
from .utils import sqlalchemy_model_to_pydantic
from .viewset import ViewSet


FRONTEND_PACKAGE = "fastapi_rest_toolkit.admin_frontend"


@dataclass(slots=True)
class ModelAdmin:
    model: Type[DeclarativeBase]
    label: str | None = None
    group: str = "管理"
    resource: str | None = None
    list_display: Sequence[str] | None = None
    search_fields: Sequence[str] = ()
    list_filter: Sequence[str] = ()
    ordering_fields: Sequence[str] | None = None
    readonly_fields: Sequence[str] = ()
    allowed_actions: Sequence[str] = ("list", "retrieve", "create", "update", "destroy")
    config_meta: dict[str, Any] | None = None
    permission_classes: Sequence[Type[BasePermission] | BasePermission] | None = None
    authentication_classes: (
        Sequence[Type[BaseAuthentication] | BaseAuthentication] | None
    ) = None

    @property
    def resource_name(self) -> str:
        return self.resource or self.model.__tablename__

    @property
    def display_name(self) -> str:
        return self.label or self.model.__name__

    def columns(self) -> list[Column]:
        return list(self.model.__table__.columns)

    def column_names(self) -> tuple[str, ...]:
        return tuple(col.key for col in self.columns())

    def primary_key_type(self) -> type:
        pk = next((col for col in self.columns() if col.primary_key), None)
        if pk is None:
            return int
        try:
            return pk.type.python_type
        except Exception:
            return str

    def primary_key_name(self) -> str:
        pk = next((col for col in self.columns() if col.primary_key), None)
        return pk.key if pk is not None else "id"

    def resolved_list_display(self) -> tuple[str, ...]:
        if self.list_display:
            return tuple(self.list_display)
        return self.column_names()

    def resolved_ordering_fields(self) -> tuple[str, ...]:
        if self.ordering_fields is not None:
            return tuple(self.ordering_fields)
        return self.resolved_list_display()

    @staticmethod
    def column_label(col: Column) -> str:
        return str(col.info.get("name") or col.key)

    def field_config(self, field_name: str) -> dict[str, Any]:
        field_configs = (self.config_meta or {}).get("fields", {})
        if not isinstance(field_configs, dict):
            return {}
        config = field_configs.get(field_name, {})
        return config if isinstance(config, dict) else {}

    def field_meta(self) -> list[dict[str, Any]]:
        readonly = set(self.readonly_fields)
        fields = []
        for col in self.columns():
            try:
                py_type = col.type.python_type.__name__
            except Exception:
                py_type = "Any"
            fields.append(
                {
                    "name": col.key,
                    "label": self.column_label(col),
                    "type": py_type,
                    "primary_key": col.primary_key,
                    "nullable": col.nullable,
                    "readonly": col.key in readonly or col.primary_key,
                    "default": col.default is not None
                    or col.server_default is not None,
                    "max_length": getattr(col.type, "length", None),
                    "config": self.field_config(col.key),
                }
            )
        return fields

    def meta(self) -> dict[str, Any]:
        return {
            "resource": self.resource_name,
            "label": self.display_name,
            "group": self.group,
            "primary_key": self.primary_key_name(),
            "fields": self.field_meta(),
            "list_display": list(self.resolved_list_display()),
            "search_fields": list(self.search_fields),
            "list_filter": list(self.list_filter),
            "ordering_fields": list(self.resolved_ordering_fields()),
            "readonly_fields": list(self.readonly_fields),
            "allowed_actions": list(self.allowed_actions),
            "config_meta": self.config_meta or {},
        }


class AdminSite:
    def __init__(
        self,
        *,
        get_session: Callable,
        title: str = "管理后台",
        permission_classes: Sequence[Type[BasePermission] | BasePermission] = (),
        authentication_classes: Sequence[
            Type[BaseAuthentication] | BaseAuthentication
        ] = (),
    ):
        self.title = title
        self.get_session = get_session
        self.permission_classes = permission_classes
        self.authentication_classes = authentication_classes
        self.registry: dict[str, ModelAdmin] = {}
        self.router = APIRouter()
        self.router.add_api_route(
            "/", self.index, methods=["GET"], include_in_schema=False
        )
        self.router.add_api_route(
            "/assets/{asset_path:path}",
            self.asset,
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/api/meta", self.meta, methods=["GET"], tags=["admin"]
        )

    def register(
        self,
        model: Type[DeclarativeBase],
        *,
        label: str | None = None,
        group: str = "管理",
        resource: str | None = None,
        list_display: Sequence[str] | None = None,
        search_fields: Sequence[str] = (),
        list_filter: Sequence[str] = (),
        ordering_fields: Sequence[str] | None = None,
        readonly_fields: Sequence[str] = (),
        allowed_actions: Sequence[str] = (
            "list",
            "retrieve",
            "create",
            "update",
            "destroy",
        ),
        config_meta: dict[str, Any] | None = None,
        permission_classes: Sequence[Type[BasePermission] | BasePermission]
        | None = None,
        authentication_classes: Sequence[Type[BaseAuthentication] | BaseAuthentication]
        | None = None,
    ):
        admin = ModelAdmin(
            model=model,
            label=label,
            group=group,
            resource=resource,
            list_display=list_display,
            search_fields=search_fields,
            list_filter=list_filter,
            ordering_fields=ordering_fields,
            readonly_fields=readonly_fields,
            allowed_actions=allowed_actions,
            config_meta=config_meta,
            permission_classes=permission_classes,
            authentication_classes=authentication_classes,
        )
        if admin.resource_name in self.registry:
            raise RuntimeError(
                f"Admin resource already registered: {admin.resource_name}"
            )
        self.registry[admin.resource_name] = admin
        self._register_model_routes(admin)
        return self

    async def index(self, request: Request):
        base_path = request.url.path.rstrip("/")
        html = (
            self._read_frontend_file("index.html")
            .replace("__ADMIN_TITLE__", escape(self.title))
            .replace("__ADMIN_BASE_PATH__", base_path)
        )
        return HTMLResponse(html)

    async def asset(self, asset_path: str):
        if self._is_unsafe_asset_path(asset_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )
        return Response(
            self._read_frontend_bytes(f"assets/{asset_path}", not_found=True),
            media_type=self._asset_media_type(asset_path),
        )

    async def meta(self):
        groups: dict[str, list[dict[str, Any]]] = {}
        for admin in self.registry.values():
            groups.setdefault(admin.group, []).append(admin.meta())
        return {
            "title": self.title,
            "groups": [
                {"label": key, "models": value} for key, value in groups.items()
            ],
            "models": [admin.meta() for admin in self.registry.values()],
        }

    def _register_model_routes(self, admin: ModelAdmin):
        viewset_cls = self._make_viewset(admin)
        router = DefaultRouter()
        router.register(
            admin.resource_name,
            viewset_cls,
            get_session=self.get_session,
            tags=[f"admin:{admin.resource_name}"],
            pk_type=admin.primary_key_type(),
        )
        self.router.include_router(router.router, prefix="/api")

    def _make_viewset(self, admin: ModelAdmin) -> type[ViewSet]:
        site = self
        readonly = set(admin.readonly_fields)

        class AdminFilterBackend:
            reserved = {"limit", "offset", "search", "ordering"}

            def apply(self, *, request, view, filters):
                columns = {col.key: col for col in admin.columns()}
                allowed = set(admin.search_fields).union(admin.list_filter)
                for key, value in dict(request.query_params or {}).items():
                    if key in self.reserved or key not in allowed or value == "":
                        continue
                    filters[key] = self._coerce_value(columns.get(key), value)
                return filters

            @staticmethod
            def _coerce_value(column: Column | None, value: Any):
                if column is None:
                    return value
                try:
                    py_type = column.type.python_type
                except Exception:
                    return value
                if py_type is bool and isinstance(value, str):
                    return value.lower() in {"1", "true", "yes", "on"}
                if py_type is int:
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        return value
                if py_type is float:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return value
                return value

        class AdminModelViewSet(ViewSet):
            model = admin.model
            allowed_actions = tuple(admin.allowed_actions)
            permission_classes = tuple(
                admin.permission_classes
                if admin.permission_classes is not None
                else site.permission_classes
            )
            authentication_classes = tuple(
                admin.authentication_classes
                if admin.authentication_classes is not None
                else site.authentication_classes
            )
            filter_backends = (
                AdminFilterBackend(),
                SearchFilterBackend(),
                OrderingFilterBackend(),
            )
            search_fields = tuple(admin.search_fields)
            ordering_fields = tuple(admin.resolved_ordering_fields())
            read_schema: Type[BaseModel] = sqlalchemy_model_to_pydantic(
                admin.model,
                name=f"{admin.model.__name__}AdminRead",
            )
            create_schema: Type[BaseModel] = sqlalchemy_model_to_pydantic(
                admin.model,
                name=f"{admin.model.__name__}AdminCreate",
                mode="create",
                exclude=readonly,
            )
            update_schema: Type[BaseModel] = sqlalchemy_model_to_pydantic(
                admin.model,
                name=f"{admin.model.__name__}AdminUpdate",
                mode="update",
                exclude=readonly,
            )

            def __init__(self):
                self.service = CRUDService(
                    crud=CRUDPlus(admin.model), model=admin.model
                )

        AdminModelViewSet.__name__ = f"{admin.model.__name__}AdminViewSet"
        return AdminModelViewSet

    @staticmethod
    def _read_frontend_file(filename: str, *, not_found: bool = False) -> str:
        try:
            return (
                resources.files(FRONTEND_PACKAGE)
                .joinpath(filename)
                .read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            if not_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asset not found",
                ) from exc
            raise

    @staticmethod
    def _read_frontend_bytes(filename: str, *, not_found: bool = False) -> bytes:
        try:
            return resources.files(FRONTEND_PACKAGE).joinpath(filename).read_bytes()
        except FileNotFoundError as exc:
            if not_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asset not found",
                ) from exc
            raise

    @staticmethod
    def _is_unsafe_asset_path(asset_path: str) -> bool:
        parts = PurePosixPath(asset_path).parts
        return not asset_path or any(part in {"", ".", ".."} for part in parts)

    @staticmethod
    def _asset_media_type(asset_path: str) -> str:
        if asset_path.endswith(".css"):
            return "text/css; charset=utf-8"
        if asset_path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if asset_path.endswith(".woff2"):
            return "font/woff2"
        if asset_path.endswith(".woff"):
            return "font/woff"
        return "text/plain; charset=utf-8"
