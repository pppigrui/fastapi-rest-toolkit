import sys
sys.path.append("..")  # noqa
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from app.db.session import engine, get_session
from app.models.base import Base
from app.models.user import User

from app.auth.deps import get_current_user
from app.auth.jwt import encode_jwt

from fastapi_rest_toolkit.router import DefaultRouter
from app.api.users import UserViewSet
from app.exceptions import register_exception_handlers
from app.api.posts import PostViewSet



@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ARG001
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown (如果需要的话)


app = FastAPI(
    title="DRF-like FastAPI (sqlalchemy-crud-plus)",
    lifespan=lifespan,
)

# 注册异常处理器
register_exception_handlers(app)


@app.post("/auth/dev-token")
async def dev_token(user_id: int, session=Depends(get_session)):
    # Ensure user exists
    user = await session.get(User, user_id)
    if not user:
        return {"error": "user not found"}

    payload = {
        "sub": str(user_id),
        "exp": (datetime.now(timezone.utc) + timedelta(days=7)).timestamp(),
    }
    return {"access_token": encode_jwt(payload), "token_type": "bearer"}


router = DefaultRouter()
router.register(
    "users",
    UserViewSet,
    get_session=get_session,
    get_user=get_current_user,
    tags=["users"],
    pk_type=int,
)
router.register(
    "posts",
    PostViewSet,
    get_session=get_session,
    get_user=get_current_user,
    tags=["posts"],
    pk_type=int,
)
app.include_router(router.router, prefix="/api")


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
