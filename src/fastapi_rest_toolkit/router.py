from fastapi import APIRouter, Depends, Request

from .viewset import ViewSet
from .request import FRFRequest
from .utils import get_actions


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
        vs.init_schema()  # init schemas for the viewset

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

        async def destroy_ep(
            pk: pk_type, request=Depends(build_request), session=Depends(get_session)
        ):
            async with session.begin():
                return await vs.destroy(request, session, pk)

        # A dictionary that manages: endpoint, HTTP method, and is detail
        routes = {
            "list": (list_ep, "GET", False),
            "create": (create_ep, "POST", False),
            "retrieve": (retrieve_ep, "GET", True),
            "update": (update_ep, "PUT", True),
            "destroy": (destroy_ep, "DELETE", True),
        }

        for action in vs.allowed_actions:
            if action not in routes:
                continue

            func, http_method, detail = routes[action]
            if isinstance(pk_type, int):
                pk_type_str = "int"
            else:
                pk_type_str = "str"

            path = f"/{prefix}/{{pk:{pk_type_str}}}" if detail else f"/{prefix}"
            self.router.add_api_route(
                path,
                func,
                methods=[http_method],
                tags=tags,
                name=f"{prefix}_{action}",
            )

        def make_action_endpoint(action_func, detail: bool):
            if detail:
                async def endpoint(
                    pk: pk_type,
                    request=Depends(build_request),
                    session=Depends(get_session),
                ):
                    async with session.begin():
                        return await action_func(request, session, pk)
                return endpoint
            else:
                async def endpoint(
                    request=Depends(build_request),
                    session=Depends(get_session),
                ):
                    async with session.begin():
                        return await action_func(request, session)
                return endpoint

        # Register custom actions
        custom_actions = get_actions(vs)
        for action_name, action_config in custom_actions.items():
            action_func = action_config["func"]
            action_methods = action_config["methods"]
            detail = action_config["detail"]
            url_path = action_config["url_path"]

            if detail:
                path = f"/{prefix}/{{pk:{pk_type}}}/{url_path}"
            else:
                path = f"/{prefix}/{url_path}"
            action_endpoint = make_action_endpoint(action_func, detail)
            self.router.add_api_route(
                path,
                action_endpoint,
                methods=list(action_methods),
                tags=tags,
            )

        return self
