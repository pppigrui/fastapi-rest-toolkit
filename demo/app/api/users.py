from sqlalchemy_crud_plus import CRUDPlus

from app.db.redis import redis_client


from src.fastapi_rest_toolkit.viewset import ViewSet
from src.fastapi_rest_toolkit.permissions import IsAuthenticated, AllowAny
from src.fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from src.fastapi_rest_toolkit.service import CRUDService

from app.models.user import User
from app.deps.auth import UserAuthentication
from src.fastapi_rest_toolkit.decorators import action


class UserViewSet(ViewSet):
    model = User
    authentication_classes = (UserAuthentication,)  # Custom authentication

    # Demo: Requires login by default. You can change to AllowAny to open registration
    permission_classes = (
        AllowAny,
        IsAuthenticated,
    )

    search_fields = ("email", "name", "phone", "bio")
    ordering_fields = (
        "id",
        "email",
        "name",
        "age",
        "account_balance",
        "created_at",
        "last_login_at",
    )
    load_strategies = ("posts",)
    # join_conditions = ["posts"]
    throttle_classes = (AsyncRedisSimpleRateThrottle(redis=redis_client),)

    def __init__(self):
        user_crud = CRUDPlus(User)
        self.service = CRUDService(crud=user_crud, model=User)

    @action(methods=["get"], detail=False)
    async def hello(self, request, session):
        return {"message": "Hello, World!"}
