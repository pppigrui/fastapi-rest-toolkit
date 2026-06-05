from sqlalchemy_crud_plus import CRUDPlus


from src.fastapi_rest_toolkit.viewset import ViewSet
from src.fastapi_rest_toolkit.permissions import AllowAny
from src.fastapi_rest_toolkit.throttle import AnonRateThrottle
from src.fastapi_rest_toolkit.service import CRUDService

from app.models.post import Post

AnonRateThrottle.THROTTLE_RATES.update(
    {
        "anon": "10/minute",
    }
)


class PostViewSet(ViewSet):
    model = Post
    permission_classes = (AllowAny,)

    search_fields = ("title", "content")
    ordering_fields = ("id", "title", "created_at")
    throttle_classes = (AnonRateThrottle(),)

    def __init__(self):
        post_crud = CRUDPlus(Post)
        self.service = CRUDService(crud=post_crud, model=Post)
