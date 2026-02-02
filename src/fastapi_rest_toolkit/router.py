from fastapi import APIRouter, Depends, Request

from .viewset import ViewSet
from .request import FRFRequest


class DefaultRouter:
    def __init__(self):
        self.router = APIRouter()

    def register(
        self,
        prefix: str,
        viewset_cls: ViewSet,
        *,
        get_session,
        tags=None,
        pk_type=int,
    ):
        vs: ViewSet = viewset_cls()

        async def build_request(req: Request) -> FRFRequest:
            return await FRFRequest.from_fastapi(req)

        async def list_ep(request=Depends(build_request), session=Depends(get_session)):
            async with session.begin():
                return await vs.list(request, session)

        async def create_ep(request=Depends(build_request), session=Depends(get_session)):
            async with session.begin():
                return await vs.create(request, session)

        async def retrieve_ep(
            pk: pk_type, request=Depends(build_request), session=Depends(get_session)
        ):
            async with session.begin():
                return await vs.retrieve(request, session, pk)

        async def update_ep(
            pk: pk_type, request=Depends(build_request), session=Depends(get_session)
        ):
            async with session.begin():
                return await vs.update(request, session, pk)

        async def patch_ep(
            pk: pk_type, request=Depends(build_request), session=Depends(get_session)
        ):
            async with session.begin():
                return await vs.partial_update(request, session, pk)

        async def delete_ep(
            pk: pk_type, request=Depends(build_request), session=Depends(get_session)
        ):
            async with session.begin():
                return await vs.destroy(request, session, pk)

        # 一个字典同时管理：endpoint、HTTP 方法、是否 detail
        routes = {
            "list": (list_ep, "GET", False),
            "create": (create_ep, "POST", False),
            "retrieve": (retrieve_ep, "GET", True),
            "update": (update_ep, "PUT", True),
            "partial_update": (patch_ep, "PATCH", True),
            "destroy": (delete_ep, "DELETE", True),
        }

        for action in vs.allowed_methods:
            if action not in routes:
                continue

            func, http_method, detail = routes[action]
            path = f"/{prefix}/{{pk}}" if detail else f"/{prefix}"

            self.router.add_api_route(
                path,
                func,
                methods=[http_method],
                tags=tags,
            )

        return self
