from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum as PythonEnum
from html import escape
from inspect import Parameter, isawaitable, signature
from io import StringIO
from importlib import resources
from pathlib import PurePosixPath
from typing import Any, Callable, Sequence, Type

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import Column, Enum as SQLAlchemyEnum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy_crud_plus import CRUDPlus

from .authentication import BaseAuthentication
from .filters import OrderingFilterBackend, SearchFilterBackend
from .permissions import BasePermission
from .request import FRFRequest
from .router import DefaultRouter
from .service import CRUDService
from .utils import sqlalchemy_model_to_pydantic
from .viewset import ViewSet


FRONTEND_PACKAGE = "fastapi_rest_toolkit.admin_frontend"
ADMIN_CSV_EXPORT_LIMIT = 10000


@dataclass(slots=True)
class AdminAction:
    name: str
    label: str
    handler: Callable[..., Any]
    scope: str = "bulk"
    confirmation: str | None = None
    variant: str = "primary"

    def __post_init__(self):
        if self.scope not in {"bulk", "row", "both"}:
            raise ValueError("AdminAction.scope must be one of: bulk, row, both")
        if not self.name:
            raise ValueError("AdminAction.name is required")
        if not callable(self.handler):
            raise TypeError("AdminAction.handler must be callable")

    @property
    def supports_bulk(self) -> bool:
        return self.scope in {"bulk", "both"}

    @property
    def supports_row(self) -> bool:
        return self.scope in {"row", "both"}

    def meta(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "scope": self.scope,
            "confirmation": self.confirmation,
            "variant": self.variant,
        }


@dataclass(slots=True)
class AdminDisplayMethod:
    name: str
    label: str
    handler: Callable[..., Any]
    type: str = "str"
    config: dict[str, Any] | None = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("AdminDisplayMethod.name is required")
        if not callable(self.handler):
            raise TypeError("AdminDisplayMethod.handler must be callable")


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
    fieldsets: Sequence[Any] | None = None
    actions: Sequence[AdminAction] = ()
    display_methods: Mapping[str, AdminDisplayMethod] | None = None
    list_editable: Sequence[str] = ()
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
        columns = set(self.column_names())
        if self.ordering_fields is not None:
            return tuple(field for field in self.ordering_fields if field in columns)
        return tuple(
            field for field in self.resolved_list_display() if field in columns
        )

    def resolved_list_editable(self) -> tuple[str, ...]:
        return tuple(self.list_editable)

    def resolved_export_fields(self) -> tuple[tuple[str, str], ...]:
        columns = {col.key: col for col in self.columns()}
        display_methods = self.display_methods or {}
        fields = []
        for name in self.resolved_list_display():
            method = display_methods.get(name)
            config = self.field_config(name) or (method.config if method else {}) or {}
            if config.get("hidden") or config.get("table_hidden"):
                continue
            col = columns.get(name)
            if col is not None:
                label = self.column_label(col)
            else:
                label = method.label if method is not None else name
            fields.append((name, label))
        return tuple(fields)

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
                configured_type = col.info.get("python_type")
                if configured_type is not None:
                    py_type = getattr(configured_type, "__name__", str(configured_type))
                else:
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
                    "choices": self.field_choices(col),
                    "config": self.field_config(col.key),
                }
            )
        for method in (self.display_methods or {}).values():
            fields.append(
                {
                    "name": method.name,
                    "label": method.label,
                    "type": method.type,
                    "primary_key": False,
                    "nullable": True,
                    "readonly": True,
                    "default": True,
                    "max_length": None,
                    "choices": [],
                    "computed": True,
                    "config": method.config or {},
                }
            )
        return fields

    def field_choices(self, col: Column) -> list[dict[str, Any]]:
        configured = self.field_config(col.key).get("choices")
        choices = self._normalize_choices(configured)
        if choices:
            return choices

        if isinstance(col.type, SQLAlchemyEnum):
            enum_class = getattr(col.type, "enum_class", None)
            if enum_class is not None:
                return [
                    {"label": member.name, "value": self._choice_value(member)}
                    for member in enum_class
                ]
            return [
                {"label": str(value), "value": self._choice_value(value)}
                for value in getattr(col.type, "enums", ())
            ]

        return []

    def fieldset_meta(self) -> list[dict[str, Any]]:
        if not self.fieldsets:
            return []

        columns = set(self.column_names())
        used: set[str] = set()
        normalized = []
        for raw_fieldset in self.fieldsets:
            title, options = self._fieldset_options(raw_fieldset)
            fields = []
            for field in options.get("fields", ()):
                if field in columns and field not in used:
                    fields.append(field)
                    used.add(field)
            if not fields:
                continue

            fieldset = {
                "title": title,
                "fields": fields,
                "collapsible": bool(options.get("collapsible", False)),
                "default_collapsed": bool(options.get("default_collapsed", False)),
            }
            description = options.get("description")
            if description:
                fieldset["description"] = str(description)
            normalized.append(fieldset)

        return normalized

    @staticmethod
    def _fieldset_options(raw_fieldset: Any) -> tuple[str, Mapping[str, Any]]:
        if isinstance(raw_fieldset, Mapping):
            title = raw_fieldset.get("title") or raw_fieldset.get("name") or ""
            return str(title), raw_fieldset
        if (
            isinstance(raw_fieldset, (tuple, list))
            and len(raw_fieldset) == 2
            and isinstance(raw_fieldset[1], Mapping)
        ):
            return str(raw_fieldset[0] or ""), raw_fieldset[1]
        raise TypeError(
            "fieldsets must contain dicts or Django-style "
            "(title, {fields: (...)}) tuples"
        )

    @classmethod
    def _normalize_choices(cls, choices: Any) -> list[dict[str, Any]]:
        if not choices:
            return []

        if isinstance(choices, Mapping):
            items = [
                {"value": value, "label": label} for value, label in choices.items()
            ]
        else:
            items = list(choices)

        normalized = []
        for item in items:
            if isinstance(item, Mapping):
                value = item.get("value")
                label = item.get("label", value)
                choice = {"label": str(label), "value": cls._choice_value(value)}
                for key in ("type", "tag_type", "color"):
                    if key in item:
                        choice[key] = item[key]
                normalized.append(choice)
                continue

            if isinstance(item, (tuple, list)) and len(item) >= 2:
                value, label = item[0], item[1]
                normalized.append(
                    {"label": str(label), "value": cls._choice_value(value)}
                )
                continue

            normalized.append({"label": str(item), "value": cls._choice_value(item)})

        return normalized

    @staticmethod
    def _choice_value(value: Any) -> Any:
        if isinstance(value, PythonEnum):
            return value.value
        return value

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
            "fieldsets": self.fieldset_meta(),
            "actions": [action.meta() for action in self.actions],
            "list_editable": list(self.resolved_list_editable()),
            "config_meta": self.config_meta or {},
        }

    def action_by_name(self, name: str) -> AdminAction | None:
        return next((action for action in self.actions if action.name == name), None)


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
        fieldsets: Sequence[Any] | None = None,
        actions: Sequence[AdminAction | dict[str, Any]] = (),
        display_methods: (
            Mapping[str, Callable[..., Any] | Mapping[str, Any] | AdminDisplayMethod]
            | None
        ) = None,
        list_editable: Sequence[str] = (),
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
            fieldsets=fieldsets,
            actions=self._normalize_actions(actions),
            display_methods=self._normalize_display_methods(display_methods),
            list_editable=list_editable,
            config_meta=config_meta,
            permission_classes=permission_classes,
            authentication_classes=authentication_classes,
        )
        self._validate_admin_config(admin)
        if admin.resource_name in self.registry:
            raise RuntimeError(
                f"Admin resource already registered: {admin.resource_name}"
            )
        self.registry[admin.resource_name] = admin
        self._register_model_routes(admin)
        return self

    @staticmethod
    def _normalize_display_methods(
        display_methods: Mapping[
            str,
            Callable[..., Any] | Mapping[str, Any] | AdminDisplayMethod,
        ]
        | None,
    ) -> dict[str, AdminDisplayMethod]:
        if not display_methods:
            return {}

        normalized = {}
        for name, raw_method in display_methods.items():
            if isinstance(raw_method, AdminDisplayMethod):
                method = raw_method
            elif callable(raw_method):
                method = AdminDisplayMethod(
                    name=name,
                    label=name,
                    handler=raw_method,
                )
            elif isinstance(raw_method, Mapping):
                config = raw_method.get("config")
                if config is None:
                    config = {
                        key: raw_method[key]
                        for key in ("hidden", "table_hidden", "detail_hidden", "width")
                        if key in raw_method
                    }
                if not isinstance(config, dict):
                    raise TypeError("display method config must be a dict")
                method = AdminDisplayMethod(
                    name=name,
                    label=str(raw_method.get("label") or name),
                    handler=raw_method.get("handler"),
                    type=str(raw_method.get("type") or "str"),
                    config=config,
                )
            else:
                raise TypeError("display_methods values must be callables or dicts")
            if method.name in normalized:
                raise RuntimeError(
                    f"Admin display method already registered: {method.name}"
                )
            normalized[method.name] = method
        return normalized

    @staticmethod
    def _normalize_actions(
        actions: Sequence[AdminAction | dict[str, Any]],
    ) -> tuple[AdminAction, ...]:
        normalized = []
        names = set()
        for action in actions:
            admin_action = (
                action if isinstance(action, AdminAction) else AdminAction(**action)
            )
            if admin_action.name in names:
                raise RuntimeError(
                    f"Admin action already registered: {admin_action.name}"
                )
            names.add(admin_action.name)
            normalized.append(admin_action)
        return tuple(normalized)

    @staticmethod
    def _validate_admin_config(admin: ModelAdmin):
        columns = {col.key: col for col in admin.columns()}
        display_methods = admin.display_methods or {}
        for name in display_methods:
            if name in columns:
                raise RuntimeError(
                    f"Admin display method conflicts with model field: {name}"
                )

        list_display = set(admin.resolved_list_display())
        readonly = set(admin.readonly_fields)
        for name in admin.list_editable:
            col = columns.get(name)
            if col is None:
                raise RuntimeError(f"list_editable field is not a model field: {name}")
            if name not in list_display:
                raise RuntimeError(
                    f"list_editable field must be in list_display: {name}"
                )
            if col.primary_key or name in readonly:
                raise RuntimeError(f"list_editable field cannot be readonly: {name}")
            config = admin.field_config(name)
            if config.get("hidden") or config.get("table_hidden"):
                raise RuntimeError(f"list_editable field cannot be hidden: {name}")

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
        if "list" in admin.allowed_actions:
            self._register_export_route(admin, viewset_cls)
        router = DefaultRouter()
        router.register(
            admin.resource_name,
            viewset_cls,
            get_session=self.get_session,
            tags=[f"admin:{admin.resource_name}"],
            pk_type=admin.primary_key_type(),
        )
        self.router.include_router(router.router, prefix="/api")
        self._register_action_routes(admin, viewset_cls)

    def _register_export_route(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
    ):
        self.router.add_api_route(
            f"/api/{admin.resource_name}/export.csv",
            self._make_export_endpoint(admin, viewset_cls),
            methods=["GET"],
            tags=[f"admin:{admin.resource_name}"],
            name=f"{admin.resource_name}_export_csv",
        )

    def _make_export_endpoint(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
    ):
        async def build_request(req: Request) -> FRFRequest:
            return await FRFRequest.from_fastapi(req)

        async def endpoint(
            request=Depends(build_request),
            session=Depends(self.get_session),
        ):
            async with session.begin():
                return await self._export_csv(
                    admin,
                    viewset_cls,
                    request=request,
                    session=session,
                )

        return endpoint

    async def _export_csv(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
        *,
        request: FRFRequest,
        session,
    ) -> Response:
        view = viewset_cls()
        await view._check(request, session=session)
        filters = view.get_filters(request)
        _, items = await view.service.list(
            session,
            filters=filters,
            limit=self._csv_export_limit(request),
            offset=0,
            ordering=request.ordering,
            load_strategies=view.load_strategies,
            join_conditions=view.join_conditions,
        )
        body = self._build_csv(admin, view.serialize_many(items))
        filename = f"{admin.resource_name}.csv"
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @staticmethod
    def _csv_export_limit(request: FRFRequest) -> int:
        raw = (request.query_params or {}).get("export_limit")
        if not raw:
            return ADMIN_CSV_EXPORT_LIMIT
        try:
            limit = int(raw)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="export_limit must be an integer",
            ) from exc
        return max(1, min(limit, ADMIN_CSV_EXPORT_LIMIT))

    @classmethod
    def _build_csv(cls, admin: ModelAdmin, rows: list[dict[str, Any]]) -> bytes:
        fields = admin.resolved_export_fields()
        choice_labels = cls._csv_choice_labels(admin, fields)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([label for _, label in fields])
        for row in rows:
            writer.writerow(
                [
                    cls._format_csv_value(choice_labels.get(name, {}), row.get(name))
                    for name, _ in fields
                ]
            )
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def _csv_choice_labels(
        admin: ModelAdmin,
        fields: Sequence[tuple[str, str]],
    ) -> dict[str, dict[str, Any]]:
        columns = {col.key: col for col in admin.columns()}
        labels = {}
        for field_name, _ in fields:
            col = columns.get(field_name)
            if col is None:
                continue
            labels[field_name] = {
                str(choice.get("value")): choice.get("label", choice.get("value"))
                for choice in admin.field_choices(col)
            }
        return labels

    @staticmethod
    def _format_csv_value(choices: Mapping[str, Any], value: Any) -> Any:
        if value is None:
            return ""
        comparable = value.value if isinstance(value, PythonEnum) else value
        if str(comparable) in choices:
            return choices[str(comparable)]
        if isinstance(value, PythonEnum):
            return value.value
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _register_action_routes(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
    ):
        pk_type = admin.primary_key_type()
        for action in admin.actions:
            if action.supports_bulk:
                self.router.add_api_route(
                    f"/api/{admin.resource_name}/actions/{action.name}",
                    self._make_action_endpoint(
                        admin,
                        viewset_cls,
                        action,
                        detail=False,
                    ),
                    methods=["POST"],
                    tags=[f"admin:{admin.resource_name}"],
                    name=f"{admin.resource_name}_{action.name}_bulk_action",
                )
            if action.supports_row:
                self.router.add_api_route(
                    f"/api/{admin.resource_name}/{{pk}}/actions/{action.name}",
                    self._make_action_endpoint(
                        admin,
                        viewset_cls,
                        action,
                        detail=True,
                        pk_type=pk_type,
                    ),
                    methods=["POST"],
                    tags=[f"admin:{admin.resource_name}"],
                    name=f"{admin.resource_name}_{action.name}_row_action",
                )

    def _make_action_endpoint(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
        action: AdminAction,
        *,
        detail: bool,
        pk_type: type = str,
    ):
        async def build_request(req: Request) -> FRFRequest:
            return await FRFRequest.from_fastapi(req)

        if detail:

            async def endpoint(
                pk: pk_type,
                request=Depends(build_request),
                session=Depends(self.get_session),
            ):
                async with session.begin():
                    return await self._run_admin_action(
                        admin,
                        viewset_cls,
                        action,
                        request=request,
                        session=session,
                        pk=pk,
                    )

            endpoint.__annotations__["pk"] = pk_type
            return endpoint

        async def endpoint(
            request=Depends(build_request),
            session=Depends(self.get_session),
        ):
            async with session.begin():
                return await self._run_admin_action(
                    admin,
                    viewset_cls,
                    action,
                    request=request,
                    session=session,
                )

        return endpoint

    async def _run_admin_action(
        self,
        admin: ModelAdmin,
        viewset_cls: type[ViewSet],
        action: AdminAction,
        *,
        request: FRFRequest,
        session,
        pk: Any | None = None,
    ):
        view = viewset_cls()
        await view._check(request, session=session)
        payload = request.data if isinstance(request.data, dict) else {}

        if pk is not None:
            obj = await view.service.retrieve(session, pk=pk)
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Not found",
                )
            await view.check_object_permissions(request, obj)
            result = await self._call_action_handler(
                action,
                request=request,
                session=session,
                model_admin=admin,
                payload=payload,
                pk=pk,
                obj=obj,
            )
            return result or {"message": f"{action.label}成功"}

        pks = payload.get("pks")
        if not isinstance(pks, list) or not pks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pks must be a non-empty list",
            )
        pk_type = admin.primary_key_type()
        try:
            pks = [pk_type(value) for value in pks]
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pks contain invalid primary key values",
            ) from exc
        result = await self._call_action_handler(
            action,
            request=request,
            session=session,
            model_admin=admin,
            payload=payload,
            pks=pks,
        )
        return result or {"message": f"{action.label}成功"}

    @staticmethod
    async def _call_action_handler(action: AdminAction, **kwargs):
        params = signature(action.handler).parameters
        accepts_kwargs = any(
            param.kind == Parameter.VAR_KEYWORD for param in params.values()
        )
        call_kwargs = (
            kwargs
            if accepts_kwargs
            else {key: value for key, value in kwargs.items() if key in params}
        )
        result = action.handler(**call_kwargs)
        if isawaitable(result):
            return await result
        return result

    def _make_viewset(self, admin: ModelAdmin) -> type[ViewSet]:
        site = self
        readonly = set(admin.readonly_fields)

        class AdminFilterBackend:
            reserved = {"limit", "offset", "search", "ordering"}
            range_operators = {"gte", "lte"}

            def apply(self, *, request, view, filters):
                columns = {col.key: col for col in admin.columns()}
                exact_allowed = set(admin.search_fields).union(admin.list_filter)
                range_allowed = set(admin.list_filter)
                for key, value in dict(request.query_params or {}).items():
                    if key in self.reserved or value == "":
                        continue
                    field_name, operator = self._filter_key(key)
                    if operator:
                        if (
                            operator not in self.range_operators
                            or field_name not in range_allowed
                        ):
                            continue
                        filters[key] = self._coerce_value(
                            columns.get(field_name), value
                        )
                        continue
                    if field_name not in exact_allowed:
                        continue
                    filters[key] = self._coerce_value(columns.get(field_name), value)
                return filters

            @staticmethod
            def _filter_key(key: str) -> tuple[str, str | None]:
                if "__" not in key:
                    return key, None
                field_name, _, operator = key.rpartition("__")
                return field_name, operator

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
                if py_type is datetime and isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except ValueError:
                        return value
                if py_type is date and isinstance(value, str):
                    try:
                        return date.fromisoformat(value[:10])
                    except ValueError:
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

            def serialize(self, obj: Any) -> dict | BaseModel | None:
                row = super().serialize(obj)
                if obj is None or not isinstance(row, dict):
                    return row

                for method in (admin.display_methods or {}).values():
                    row[method.name] = site._format_display_value(
                        site._call_display_handler(
                            method,
                            obj=obj,
                            row=row,
                            model_admin=admin,
                        )
                    )
                return row

        AdminModelViewSet.__name__ = f"{admin.model.__name__}AdminViewSet"
        return AdminModelViewSet

    @staticmethod
    def _call_display_handler(
        method: AdminDisplayMethod,
        *,
        obj: Any,
        row: dict[str, Any],
        model_admin: ModelAdmin,
    ):
        params = signature(method.handler).parameters
        accepts_kwargs = any(
            param.kind == Parameter.VAR_KEYWORD for param in params.values()
        )
        kwargs = {"obj": obj, "row": row, "model_admin": model_admin}
        if accepts_kwargs:
            result = method.handler(**kwargs)
        else:
            call_kwargs = {key: value for key, value in kwargs.items() if key in params}
            if call_kwargs:
                result = method.handler(**call_kwargs)
            else:
                result = method.handler(obj)
        if isawaitable(result):
            raise RuntimeError("Admin display method handlers must be synchronous")
        return result

    @staticmethod
    def _format_display_value(value: Any) -> Any:
        if isinstance(value, PythonEnum):
            return value.value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

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
