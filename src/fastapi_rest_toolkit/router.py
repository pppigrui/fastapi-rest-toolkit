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
        get_user,
        tags=None,
        pk_type=int,
    ):
        vs: ViewSet = viewset_cls()

        async def build_request(req: Request, user=Depends(get_user)):
            return await FRFRequest.from_fastapi(req, user=user)

        async def list_ep(request=Depends(build_request), session=Depends(get_session)):
            async with session.begin():
                return await vs.list(request, session)

        async def create_ep(
            request=Depends(build_request), session=Depends(get_session)
        ):
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

        self.router.add_api_route(f"/{prefix}", list_ep, methods=["GET"], tags=tags)
        self.router.add_api_route(f"/{prefix}", create_ep, methods=["POST"], tags=tags)
        self.router.add_api_route(
            f"/{prefix}" + "/{pk}", retrieve_ep, methods=["GET"], tags=tags
        )
        self.router.add_api_route(
            f"/{prefix}" + "/{pk}", update_ep, methods=["PUT"], tags=tags
        )
        self.router.add_api_route(
            f"/{prefix}" + "/{pk}", patch_ep, methods=["PATCH"], tags=tags
        )
        self.router.add_api_route(
            f"/{prefix}" + "/{pk}", delete_ep, methods=["DELETE"], tags=tags
        )

        return self
