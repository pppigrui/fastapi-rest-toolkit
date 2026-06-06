import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy import update

from app.db.session import engine, get_session
from app.models.base import Base
from app.models.user import User
from app.models.post import Post
from app.models.agent import Agent

from app.auth.jwt import encode_jwt

from src.fastapi_rest_toolkit.router import DefaultRouter
from src.fastapi_rest_toolkit.admin import AdminAction, AdminSite
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


async def activate_users(*, session, pks):
    await session.execute(update(User).where(User.id.in_(pks)).values(is_active=True))
    return {"message": f"已激活 {len(pks)} 个用户"}


async def deactivate_user(*, session, pk):
    await session.execute(update(User).where(User.id == pk).values(is_active=False))
    return {"message": "已停用用户"}


def user_status_text(*, row):
    return "启用" if row.get("is_active") else "停用"


def post_content_length(*, row):
    return len(row.get("content") or "")


admin.register(
    Agent,
    label="Agent 配置",
    group="AI",
    list_display=("id", "code", "name", "model", "description", "created_at"),
    list_editable=("name", "model"),
    search_fields=("code", "name", "description", "prompt", "model"),
    list_filter=("model", "created_at"),
    ordering_fields=("id", "code", "name", "model", "created_at"),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("基础信息", {"fields": ("code", "name", "description", "model")}),
        ("提示词", {"fields": ("prompt",)}),
        ("能力配置", {"fields": ("setting", "tools", "parameters")}),
    ),
    config_meta={
        "icon": "fa-solid fa-robot",
        "fields": {
            "code": {
                "placeholder": "请输入唯一编码，例如 chat_ai",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请输入编码", "trigger": "blur"},
                ],
            },
            "name": {
                "placeholder": "请输入名称",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请输入名称", "trigger": "blur"},
                ],
            },
            "description": {
                "widget": "textarea",
                "placeholder": "请输入描述",
                "width": 180,
            },
            "prompt": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入系统提示词",
                "help_text": "Agent 的系统提示词，会作为模型回答的基础指令。",
            },
            "model": {
                "placeholder": "请输入模型名称",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请输入模型名称", "trigger": "blur"},
                ],
            },
            "setting": {
                "widget": "json",
                "table_hidden": True,
                "placeholder": (
                    "{\n"
                    '  "enable_user_memory": true,\n'
                    '  "enable_session_memory": true,\n'
                    '  "session_memory_expire": 604800\n'
                    "}"
                ),
                "help_text": "JSON 对象，用于配置用户记忆、会话记忆等开关。",
            },
            "tools": {
                "widget": "json",
                "table_hidden": True,
                "placeholder": "[]",
                "help_text": "JSON 数组，用于声明 Agent 可调用的工具。",
            },
            "parameters": {
                "widget": "json",
                "table_hidden": True,
                "placeholder": (
                    "{\n"
                    '  "top_p": 0.95,\n'
                    '  "max_tokens": 4096,\n'
                    '  "temperature": 0.5,\n'
                    '  "presence_penalty": 0.4\n'
                    "}"
                ),
                "help_text": "JSON 对象，用于配置模型推理参数。",
            },
            "created_at": {
                "form_hidden": True,
                "width": 180,
            },
        },
    },
)
admin.register(
    User,
    label="用户管理",
    group="Demo",
    list_display=(
        "id",
        "name",
        "email",
        "role",
        "age",
        "account_balance",
        "is_active",
        "is_staff",
        "status_text",
        "created_at",
    ),
    list_editable=("role", "age", "account_balance", "is_active", "is_staff"),
    search_fields=("name", "email", "phone", "bio"),
    list_filter=(
        "is_active",
        "is_staff",
        "role",
        "birthday",
        "last_login_at",
        "created_at",
    ),
    ordering_fields=(
        "id",
        "name",
        "email",
        "age",
        "account_balance",
        "role",
        "created_at",
        "last_login_at",
    ),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("基础信息", {"fields": ("name", "email", "phone", "bio")}),
        ("状态权限", {"fields": ("role", "is_active", "is_staff")}),
        (
            "数值日期",
            {"fields": ("age", "account_balance", "birthday", "last_login_at")},
        ),
    ),
    actions=(
        AdminAction(
            name="activate",
            label="批量启用",
            handler=activate_users,
            scope="bulk",
            confirmation="确认启用选中的用户？",
            variant="success",
        ),
        AdminAction(
            name="deactivate",
            label="停用",
            handler=deactivate_user,
            scope="row",
            confirmation="确认停用这个用户？",
            variant="warning",
        ),
    ),
    display_methods={
        "status_text": {
            "label": "状态文本",
            "handler": user_status_text,
            "width": 100,
        },
    },
    config_meta={
        "icon": "fa-solid fa-user",
        "fields": {
            "name": {
                "placeholder": "请输入姓名",
                "width": 140,
            },
            "email": {
                "placeholder": "请输入邮箱",
                "width": 220,
                "rules": [
                    {"required": True, "message": "请输入邮箱", "trigger": "blur"},
                    {"type": "email", "message": "请输入正确的邮箱", "trigger": "blur"},
                ],
            },
            "phone": {
                "placeholder": "请输入手机号",
                "width": 150,
            },
            "bio": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入个人简介",
                "help_text": "Text 长文本字段演示，适合放较长的备注或说明。",
            },
            "role": {
                "widget": "select",
                "width": 120,
                "choices": [
                    {"label": "普通用户", "value": "member", "type": "info"},
                    {"label": "编辑", "value": "editor", "type": "warning"},
                    {"label": "管理员", "value": "admin", "type": "success"},
                ],
            },
            "age": {
                "widget": "number",
                "width": 100,
            },
            "account_balance": {
                "widget": "number",
                "width": 130,
            },
            "birthday": {
                "widget": "date",
                "width": 150,
            },
            "is_active": {
                "widget": "switch",
                "width": 120,
            },
            "is_staff": {
                "widget": "switch",
                "width": 120,
            },
            "last_login_at": {
                "widget": "datetime",
                "width": 180,
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
    list_display=(
        "id",
        "title",
        "category",
        "status",
        "is_published",
        "view_count",
        "rating",
        "priority",
        "author_id",
        "content_length",
        "created_at",
    ),
    list_editable=(
        "title",
        "category",
        "status",
        "is_published",
        "priority",
        "rating",
    ),
    search_fields=("title", "summary", "content", "category"),
    list_filter=(
        "author_id",
        "category",
        "status",
        "is_published",
        "publish_date",
        "published_at",
        "created_at",
    ),
    ordering_fields=(
        "id",
        "title",
        "category",
        "status",
        "view_count",
        "rating",
        "priority",
        "publish_date",
        "published_at",
        "created_at",
    ),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("文章信息", {"fields": ("title", "author_id", "category", "status")}),
        (
            "发布控制",
            {"fields": ("is_published", "publish_date", "published_at", "priority")},
        ),
        (
            "内容",
            {
                "fields": ("summary", "content"),
                "description": "长文本字段使用独立分组。",
            },
        ),
        ("指标", {"fields": ("view_count", "rating")}),
    ),
    display_methods={
        "content_length": {
            "label": "内容字数",
            "handler": post_content_length,
            "type": "int",
            "width": 100,
        },
    },
    config_meta={
        "icon": "fa-solid fa-file-lines",
        "fields": {
            "title": {
                "placeholder": "请输入标题",
                "width": 220,
            },
            "author_id": {
                "widget": "autocomplete",
                "resource": "users",
                "label_field": "name",
                "search_fields": ("name", "email"),
                "placeholder": "请选择作者",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请选择作者", "trigger": "change"},
                ],
            },
            "summary": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入摘要",
                "help_text": "Text 长文本字段演示，可用于列表摘要或 SEO 描述。",
            },
            "content": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入正文内容",
                "help_text": "长文本字段适合使用 textarea。",
            },
            "category": {
                "widget": "select",
                "width": 120,
                "choices": [
                    {"label": "技术", "value": "tech", "type": "primary"},
                    {"label": "产品", "value": "product", "type": "success"},
                    {"label": "运营", "value": "ops", "type": "warning"},
                    {"label": "公告", "value": "notice", "type": "info"},
                ],
            },
            "status": {
                "widget": "select",
                "width": 120,
                "choices": [
                    {"label": "草稿", "value": "draft", "type": "info"},
                    {"label": "审核中", "value": "reviewing", "type": "warning"},
                    {"label": "已发布", "value": "published", "type": "success"},
                    {"label": "已归档", "value": "archived", "type": "info"},
                ],
            },
            "is_published": {
                "widget": "switch",
                "width": 120,
            },
            "view_count": {
                "widget": "number",
                "width": 110,
            },
            "rating": {
                "widget": "number",
                "width": 100,
            },
            "priority": {
                "widget": "number",
                "width": 100,
            },
            "publish_date": {
                "widget": "date",
                "width": 150,
            },
            "published_at": {
                "widget": "datetime",
                "width": 180,
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
