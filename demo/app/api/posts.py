from sqlalchemy_crud_plus import CRUDPlus

from app.db.redis import redis_client

from src.fastapi_rest_toolkit.viewset import ViewSet
from src.fastapi_rest_toolkit.permissions import IsAuthenticated, AllowAny
from src.fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from src.fastapi_rest_toolkit.service import CRUDService

from app.models.post import Post


class PostViewSet(ViewSet):
    model = Post

    permission_classes = (
        AllowAny,
        IsAuthenticated,
    )

    search_fields = ("title", "content")
    ordering_fields = ("id", "title", "created_at")
    throttle_classes = (AsyncRedisSimpleRateThrottle(redis=redis_client),)

    def __init__(self):
        post_crud = CRUDPlus(Post)
        self.service = CRUDService(crud=post_crud, model=Post)
