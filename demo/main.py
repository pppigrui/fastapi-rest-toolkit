import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends

from app.db.session import engine, get_session
from app.models.base import Base
from app.models.user import User
from app.models.post import Post

from app.auth.jwt import encode_jwt

from src.fastapi_rest_toolkit.router import DefaultRouter
from src.fastapi_rest_toolkit.admin import AdminSite
from app.api.users import UserViewSet
from app.exceptions import register_exception_handlers
from app.api.posts import PostViewSet


@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ARG001
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="DRF-like FastAPI (sqlalchemy-crud-plus)",
    lifespan=lifespan,
)

# Register exception handlers
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
router.register("users", UserViewSet, get_session=get_session)
router.register("posts", PostViewSet, get_session=get_session)
app.include_router(router.router, prefix="/api")

admin = AdminSite(get_session=get_session, title="FastAPI REST Toolkit 管理后台")
admin.register(
    User,
    label="用户管理",
    group="Demo",
    list_display=("id", "name", "email", "is_active", "created_at"),
    search_fields=("name", "email"),
    list_filter=("is_active",),
    ordering_fields=("id", "name", "email", "created_at"),
    readonly_fields=("id", "created_at"),
    config_meta={
        "icon": "fa-solid fa-user",
        "fields": {
            "email": {
                "placeholder": "请输入邮箱",
                "width": 220,
                "rules": [
                    {"required": True, "message": "请输入邮箱", "trigger": "blur"},
                    {"type": "email", "message": "请输入正确的邮箱", "trigger": "blur"},
                ],
            },
            "is_active": {
                "widget": "switch",
                "width": 120,
            },
            "created_at": {
                "form_hidden": True,
                "width": 180,
            },
        },
    },
)
admin.register(
    Post,
    label="文章管理",
    group="Demo",
    list_display=("id", "title", "author_id", "created_at"),
    search_fields=("title", "content"),
    list_filter=("author_id",),
    ordering_fields=("id", "title", "author_id", "created_at"),
    readonly_fields=("id", "created_at"),
    config_meta={
        "icon": "fa-solid fa-file-lines",
        "fields": {
            "author_id": {
                "widget": "select",
                "resource": "users",
                "label_field": "name",
                "placeholder": "请选择作者",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请选择作者", "trigger": "change"},
                ],
            },
            "content": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入正文内容",
                "help_text": "长文本字段适合使用 textarea。",
            },
            "created_at": {
                "form_hidden": True,
                "width": 180,
            },
        },
    },
)
app.include_router(admin.router, prefix="/admin")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
