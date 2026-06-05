# FastAPI REST Toolkit

FastAPI REST Toolkit 是一个类 Django REST Framework 风格的 FastAPI 工具包。

它围绕 SQLAlchemy async model、`sqlalchemy-crud-plus` 和 FastAPI router，提供 ViewSet、自动路由、认证、权限、过滤、排序、分页、限流和自定义 action 等常用 REST API 能力。

## 特性

- ViewSet：提供 `list`、`retrieve`、`create`、`update`、`destroy` 标准 CRUD action
- DefaultRouter：按 ViewSet 自动注册 REST 路由
- Schema 自动生成：可从 SQLAlchemy model 生成 Pydantic schema
- 认证：提供 `BaseAuthentication` 和 `BearerAuthentication`
- 权限：内置 `AllowAny`、`IsAuthenticated`、`IsAdmin`
- 过滤：支持普通 query 参数过滤、`search` 搜索和 `ordering` 排序
- 分页：内置 limit/offset 分页
- 关系加载：透传 `load_strategies`、`join_conditions` 给 `sqlalchemy-crud-plus`
- 限流：支持内存限流和 Redis 异步限流
- 自定义 action：支持类似 DRF 的 `@action`

## 使用方法示例

```python
# 使用demo
from contextlib import asynccontextmanager
from fastapi_rest_toolkit import AllowAny, CRUDService, DefaultRouter, ViewSet
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi import FastAPI
from sqlalchemy_crud_plus import CRUDPlus

DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ARG001
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    lifespan=lifespan,
)


class UserViewSet(ViewSet):
    model = User
    permission_classes = (AllowAny,)
    search_fields = ("name", "email")
    ordering_fields = ("id", "name", "email", "created_at")

    def __init__(self):
        user_crud = CRUDPlus(User)
        self.service = CRUDService(crud=user_crud, model=User)


router = DefaultRouter()
router.register("users", UserViewSet, get_session=get_session)
app.include_router(router.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

```

## 安装

```bash
pip install fastapi-rest-toolkit
```

Redis 限流需要安装可选依赖：

```bash
pip install "fastapi-rest-toolkit[redis]"
```

本项目当前要求 Python `>=3.12`。

## 本地运行 demo

在项目根目录运行：

```bash
uv run demo/main.py
```

启动后访问：

```text
http://127.0.0.1:8000/docs
```

demo 包含两个资源：

- `users`：演示 Bearer JWT 认证、权限、Redis 限流、搜索、排序、关系预加载和自定义 action
- `posts`：演示匿名访问、匿名限流、搜索、排序和外键字段

demo 的主要路由：

```text
POST   /auth/dev-token?user_id=1
GET    /api/users
POST   /api/users
GET    /api/users/{pk}
PUT    /api/users/{pk}
DELETE /api/users/{pk}
GET    /api/users/hello
GET    /api/posts
POST   /api/posts
GET    /api/posts/{pk}
PUT    /api/posts/{pk}
DELETE /api/posts/{pk}
```

## 快速开始

下面是最小结构，和 demo 的写法保持一致。

```python
from fastapi import FastAPI
from sqlalchemy_crud_plus import CRUDPlus

from fastapi_rest_toolkit import AllowAny, CRUDService, DefaultRouter, ViewSet
from app.db.session import get_session
from app.models.post import Post


class PostViewSet(ViewSet):
    model = Post
    permission_classes = (AllowAny,)
    search_fields = ("title", "content")
    ordering_fields = ("id", "title", "created_at")

    def __init__(self):
        post_crud = CRUDPlus(Post)
        self.service = CRUDService(crud=post_crud, model=Post)


app = FastAPI()
router = DefaultRouter()

router.register(
    "posts",
    PostViewSet,
    get_session=get_session,
    tags=["posts"],
)

app.include_router(router.router, prefix="/api")
```

## Admin 管理后台

`AdminSite` 可以根据 SQLAlchemy model 自动生成管理接口和内置管理页面。第一版适合快速得到一个类似 Django admin 的基础 CRUD 后台。

内置页面使用 Vue 3、JavaScript 和 Element Plus，前端代码放在 `src/fastapi_rest_toolkit/admin_frontend/`，`admin.py` 只负责注册路由、提供元数据和读取静态资源。

前端资源按职责分层：

- `assets/vendor/`：本地 Vue、Element Plus、Element Plus Icons 和 Font Awesome 静态资源，不依赖 CDN
- `assets/js/`：API 请求、图标适配、工具函数和 Vue 入口分离
- `assets/css/`：设计变量、基础样式、布局、组件和响应式样式分离

```python
from fastapi_rest_toolkit import AdminSite
from app.db.session import get_session
from app.models.user import User
from app.models.post import Post

admin = AdminSite(get_session=get_session, title="管理后台")

admin.register(
    User,
    label="用户管理",
    group="系统管理",
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
            "is_active": {"widget": "switch", "width": 120},
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)
admin.register(
    Post,
    label="文章管理",
    group="内容管理",
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
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)

app.include_router(admin.router, prefix="/admin")
```

`config_meta` 会原样透传到 `/admin/api/meta`，适合放后续前端展示和行为配置。当前内置页面会读取 `config_meta["icon"]` 作为菜单图标 class，也会读取 `config_meta["fields"]` 作为字段级配置。

`list_filter` 用于声明列表页的精确筛选字段。布尔字段会显示为“是/否”下拉，`widget="select"` 字段会复用关联资源选项，其他字段显示为输入框。

`ordering_fields` 用于声明列表页允许点击表头排序的字段；未声明时默认使用 `list_display`。

字段配置第一版支持：

- `hidden`：列表和表单都隐藏
- `table_hidden`：只在列表隐藏
- `form_hidden`：只在表单隐藏
- `detail_hidden`：只在详情隐藏
- `placeholder`：表单和查询输入占位符
- `widget`：表单控件类型，支持 `input`、`textarea`、`switch`、`number`、`select`、`date`、`datetime`
- `help_text`：表单字段下方提示
- `width`：列表列宽
- `rules`：Element Plus 表单校验规则

如果字段没有显式配置 `rules`，内置页面会对“非空、无默认值、可编辑、非布尔”的字段自动生成必填规则。

`widget="select"` 会读取同级配置：

- `resource`：选项来源资源，比如 `users`
- `label_field`：选项展示字段，比如 `name`
- `value_field`：选项值字段，默认使用目标资源主键
- `limit`：选项加载数量，默认 `100`

启动后访问：

```text
http://127.0.0.1:8000/admin
```

自动生成的接口在 `/admin/api` 下：

- `GET /admin/api/meta`：后台菜单、字段、表格列和表单元数据
- `GET /admin/api/{resource}`：列表
- `POST /admin/api/{resource}`：新增
- `GET /admin/api/{resource}/{pk}`：详情
- `PUT /admin/api/{resource}/{pk}`：修改
- `DELETE /admin/api/{resource}/{pk}`：删除

内置页面支持多选后批量删除。当前批量删除会复用单条删除接口逐条执行，完成后统一刷新列表并提示成功/失败数量。

只要配置了 `model`，`ViewSet.init_schema()` 会自动生成：

- `read_schema`：包含所有表字段
- `create_schema`：排除自增主键和 `server_default` 字段
- `update_schema`：所有字段都是可选字段

也可以显式配置自己的 `read_schema`、`create_schema`、`update_schema`。

## Model 示例

demo 中的 `Post` 和 `User` 是普通 SQLAlchemy async model：

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(1000))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author: Mapped["User"] = relationship(back_populates="posts")
```

如果只需要返回用户 id，`author_id` 已经是普通字段，不需要配置关系加载。

如果需要查询 posts 时顺便加载用户对象：

```python
class PostViewSet(ViewSet):
    model = Post
    load_strategies = ("author",)
```

注意：自动生成的 schema 只包含表字段，不会自动序列化 relationship。要在响应中返回 `author` 的详细信息，需要自定义 `read_schema` 或重写 `serialize()`。

## Router

`DefaultRouter.register()` 会实例化 ViewSet、初始化 schema、校验配置并注册路由。

```python
router.register(
    prefix="users",
    viewset_cls=UserViewSet,
    get_session=get_session,
    tags=["users"],
    pk_type=int,
)
```

默认支持的 action：


| Action     | Method   | Path              |
| ---------- | -------- | ----------------- |
| `list`     | `GET`    | `/api/users`      |
| `create`   | `POST`   | `/api/users`      |
| `retrieve` | `GET`    | `/api/users/{pk}` |
| `update`   | `PUT`    | `/api/users/{pk}` |
| `destroy`  | `DELETE` | `/api/users/{pk}` |


可以通过 `allowed_actions` 控制启用的 action：

```python
class ReadOnlyPostViewSet(ViewSet):
    model = Post
    allowed_actions = ("list", "retrieve")
```

## ViewSet 配置

常用配置项：

```python
class ExampleViewSet(ViewSet):
    model = None
    service = None

    read_schema = None
    create_schema = None
    update_schema = None

    authentication_classes = ()
    permission_classes = ()
    throttle_classes = ()

    filter_backends = (
        CRUDPlusFilterBackend(),
        SearchFilterBackend(),
        OrderingFilterBackend(),
    )
    search_fields = ()
    ordering_fields = ()

    pagination = LimitOffsetPagination()
    load_strategies = None
    join_conditions = None
    allowed_actions = ("list", "retrieve", "create", "update", "destroy")
```

`service` 必须提供标准 CRUD 方法。demo 使用 `CRUDService(CRUDPlus(Model), Model)`。

## 过滤、搜索和排序

默认启用三个 filter backend：

- `CRUDPlusFilterBackend`：把普通 query 参数透传给 `sqlalchemy-crud-plus`
- `SearchFilterBackend`：读取 `search` 参数，对 `search_fields` 做 `LIKE`
- `OrderingFilterBackend`：读取 `ordering` 参数，只允许 `ordering_fields` 中的字段

示例：

```python
class PostViewSet(ViewSet):
    model = Post
    search_fields = ("title", "content")
    ordering_fields = ("id", "title", "created_at")
```

请求示例：

```text
GET /api/posts?title__like=%FastAPI%
GET /api/posts?search=FastAPI
GET /api/posts?ordering=-created_at
GET /api/posts?search=FastAPI&ordering=title
```

## 分页

默认分页响应：

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": []
}
```

请求参数：

```text
GET /api/posts?limit=20&offset=0
```

自定义分页：

```python
from fastapi_rest_toolkit import LimitOffsetPagination


class SmallPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50


class PostViewSet(ViewSet):
    pagination = SmallPagination()
```

## 认证和权限

认证类需要继承 `BaseAuthentication` 或 `BearerAuthentication`，并返回 `(user, auth)`。

demo 中的 `UserAuthentication` 会：

1. 从 `Authorization: Bearer <token>` 读取 token
2. 解码 JWT
3. 用当前 async session 查询用户
4. 把用户挂到 `request.user`

简化示例：

```python
from typing import Any

from fastapi import HTTPException, status
from fastapi_rest_toolkit.authentication import BearerAuthentication
from fastapi_rest_toolkit.contextvar import session_var
from fastapi_rest_toolkit.request import FRFRequest


class UserAuthentication(BearerAuthentication):
    async def authenticate(self, request: FRFRequest) -> tuple[Any, Any]:
        session = session_var.get()
        token = self.get_token(request)
        if session is None or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication",
            )

        user = await load_user_from_token(session, token)
        return user, token
```

ViewSet 中使用：

```python
class UserViewSet(ViewSet):
    authentication_classes = (UserAuthentication,)
    permission_classes = (IsAuthenticated,)
```

内置权限：

- `AllowAny`：允许所有请求
- `IsAuthenticated`：要求 `request.user` 不为空
- `IsAdmin`：要求 `request.user.is_admin` 为真

多个 permission 会依次检查，全部通过才允许继续执行。

## 限流

内置限流类：

- `SimpleRateThrottle`：内存限流
- `AnonRateThrottle`：只限制匿名请求
- `AsyncRedisSimpleRateThrottle`：Redis 异步限流，适合多进程或分布式部署

demo 的 posts 使用匿名限流：

```python
from fastapi_rest_toolkit.throttle import AnonRateThrottle


AnonRateThrottle.THROTTLE_RATES.update({
    "anon": "10/minute",
})


class PostViewSet(ViewSet):
    throttle_classes = (AnonRateThrottle(),)
```

demo 的 users 使用 Redis 限流：

```python
from fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from app.db.redis import redis_client


class UserViewSet(ViewSet):
    throttle_classes = (AsyncRedisSimpleRateThrottle(redis=redis_client),)
```

限流速率格式：

```text
100/day
10/hour
5/minute
1/second
```

## 关系加载

`load_strategies` 和 `join_conditions` 会透传给 `sqlalchemy-crud-plus`。

常见写法：

```python
class UserViewSet(ViewSet):
    load_strategies = ("posts",)
```

更明确的写法：

```python
class UserViewSet(ViewSet):
    load_strategies = {"posts": "selectinload"}
```

如果需要 join：

```python
class UserViewSet(ViewSet):
    join_conditions = ["posts"]
```

或指定 join 类型：

```python
class UserViewSet(ViewSet):
    join_conditions = {"posts": "left"}
```

优先使用 `load_strategies` 解决预加载问题。只有在需要基于关联表 join 查询时，再配置 `join_conditions`。

## 自定义 action

使用 `@action` 可以注册额外路由。

```python
from fastapi_rest_toolkit import action


class UserViewSet(ViewSet):
    @action(methods=["get"], detail=False)
    async def hello(self, request, session):
        return {"message": "Hello, World!"}
```

上面的 action 会注册为：

```text
GET /api/users/hello
```

detail action 会带上 `pk`：

```python
class UserViewSet(ViewSet):
    @action(methods=["post"], detail=True, url_path="activate")
    async def activate(self, request, session, pk):
        return {"id": pk, "status": "activated"}
```

对应路由：

```text
POST /api/users/{pk}/activate
```

## 异常处理

demo 注册了数据库完整性错误处理器，把唯一约束冲突转换成更友好的响应：

```python
from sqlalchemy.exc import IntegrityError


def register_exception_handlers(app):
    app.add_exception_handler(IntegrityError, integrity_error_handler)
```

在 `demo/main.py` 中：

```python
app = FastAPI(...)
register_exception_handlers(app)
```

## Demo 目录

```text
demo/
  main.py                 # FastAPI app 入口
  app/api/users.py        # UserViewSet
  app/api/posts.py        # PostViewSet
  app/auth/jwt.py         # JWT encode/decode
  app/deps/auth.py        # Bearer 认证实现
  app/db/session.py       # async SQLAlchemy session
  app/db/redis.py         # Redis client
  app/exceptions.py       # 异常处理
  app/models/             # SQLAlchemy models
  app/schemas/            # schema 生成示例
```

## 开发

同步依赖：

```bash
uv sync
```

运行 demo：

```bash
uv run demo/main.py
```

如果只想验证锁文件和依赖声明一致：

```bash
uv lock --locked
```

## License

MIT License
