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

### 快速接入

在应用启动文件中创建 `AdminSite`，注册 SQLAlchemy 模型，然后把 `admin.router` 挂到 FastAPI：

```python
from fastapi_rest_toolkit import AdminSite
from app.db.session import get_session
from app.models.user import User
from app.models.post import Post

admin = AdminSite(get_session=get_session, title="管理后台")


def user_status_text(*, row):
    return "启用" if row.get("is_active") else "停用"

admin.register(
    User,
    label="用户管理",
    group="系统管理",
    list_display=("id", "name", "email", "is_active", "status_text", "created_at"),
    list_editable=("is_active",),
    search_fields=("name", "email"),
    list_filter=("is_active",),
    ordering_fields=("id", "name", "email", "created_at"),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("基础信息", {"fields": ("name", "email")}),
        ("状态", {"fields": ("is_active",), "description": "控制用户是否可用。"}),
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
    fieldsets=(
        ("文章信息", {"fields": ("title", "author_id")}),
        ("正文", {"fields": ("content",), "description": "长文本字段使用独立分组。"}),
    ),
    config_meta={
        "icon": "fa-solid fa-file-lines",
        "fields": {
            "author_id": {
                "widget": "autocomplete",
                "resource": "users",
                "label_field": "name",
                "search_fields": ("name", "email"),
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

本地源码运行时建议使用项目依赖环境，例如 `uv run demo/main.py`。代码里应使用正式包名 `fastapi_rest_toolkit` 导入，不建议写 `src.fastapi_rest_toolkit`，否则静态资源包 `fastapi_rest_toolkit.admin_frontend` 可能无法按正常包名加载。

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
- `GET /admin/api/{resource}/export.csv`：按当前筛选和排序导出 CSV
- `POST /admin/api/{resource}/actions/{action}`：批量自定义动作
- `POST /admin/api/{resource}/{pk}/actions/{action}`：行级自定义动作

### `admin.register()` 参数

`admin.register()` 是内置管理后台的核心配置入口。它负责把一个 SQLAlchemy model 注册成一个后台资源，并生成元数据、CRUD 接口和页面菜单。

| 参数 | 含义 |
| --- | --- |
| `model` | 必填。要注册的 SQLAlchemy model。 |
| `label` | 菜单、标题、抽屉里显示的名称；不传时使用模型类名。 |
| `group` | 左侧菜单分组；默认是 `管理`。 |
| `resource` | API 和前端资源名；不传时使用 `model.__tablename__`。例如 `users`。 |
| `list_display` | 列表表格展示字段。可包含真实模型字段和 `display_methods` 计算列。 |
| `search_fields` | 顶部搜索框参与模糊搜索的字段。 |
| `list_filter` | 查询区筛选字段。布尔字段显示是/否下拉，日期/时间字段显示范围选择器，选择类字段显示下拉。 |
| `ordering_fields` | 允许点击表头排序的真实模型字段；不传时默认使用 `list_display` 中的真实模型字段。 |
| `readonly_fields` | 只读字段。创建/编辑表单不会提交这些字段，常用于 `id`、`created_at`。 |
| `allowed_actions` | 开启哪些基础动作，默认 `list/retrieve/create/update/destroy`。可用于做只读后台。 |
| `fieldsets` | 创建、编辑、详情抽屉里的字段分组，风格接近 Django admin。 |
| `actions` | 自定义批量动作或行级动作。 |
| `display_methods` | 列表和详情里的只读计算字段。 |
| `list_editable` | 允许在列表中直接编辑的真实模型字段。 |
| `config_meta` | 透传到 `/admin/api/meta` 的前端配置；当前主要读取 `icon` 和 `fields`。 |
| `permission_classes` | 该资源专用权限类；不传时使用 `AdminSite` 默认权限。 |
| `authentication_classes` | 该资源专用认证类；不传时使用 `AdminSite` 默认认证。 |

### 字段标签

字段显示名优先读取 SQLAlchemy column 的 `info["name"]`：

```python
email = mapped_column(String(100), info={"name": "邮箱"})
```

如果没有配置 `info["name"]`，后台会使用 Python 字段名，例如 `email`。

如果字段是 JSON 列但需要特殊 Python 类型，可以在 `info["python_type"]` 中声明。例如 JSON 数组字段：

```python
tools = mapped_column(JSON, info={"name": "工具列表", "python_type": list})
```

### `fieldsets`

`fieldsets` 用于声明创建、编辑和详情抽屉的字段分组。支持 Django 风格，也支持 dict 风格：

```python
fieldsets=(
    ("基础信息", {"fields": ("name", "email")}),
    ("状态", {"fields": ("is_active",), "description": "控制用户是否可用。"}),
)
```

可用配置：

- `fields`：该分组包含的字段名。
- `description`：分组说明文字。
- `collapsible`：是否可折叠，元数据已支持。
- `default_collapsed`：默认是否折叠，元数据已支持。

未出现在 `fieldsets` 里的可见字段，会落入前端的“其他”分组。

### 字段级配置

字段级配置放在 `config_meta["fields"]` 下，key 必须是模型字段名或计算列名：

```python
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
}
```

| 配置项 | 含义 |
| --- | --- |
| `hidden` | 表格、表单、详情全部隐藏。 |
| `table_hidden` | 只在列表表格隐藏。 |
| `form_hidden` | 只在创建/编辑表单隐藏。 |
| `detail_hidden` | 只在详情视图隐藏。 |
| `placeholder` | 表单输入框和查询输入框的占位提示。 |
| `widget` | 控件类型，见下方控件表。 |
| `help_text` | 表单字段下方的辅助说明。 |
| `width` | 表格列宽，传给 Element Plus `el-table-column`。 |
| `rules` | Element Plus 表单校验规则。 |
| `choices` | 声明式选项，用于下拉、筛选和标签渲染。 |
| `resource` | 关联选择字段的目标资源名，例如 `users`。 |
| `label_field` | 关联选项显示字段，例如 `name`。 |
| `value_field` | 关联选项值字段；不传时使用目标资源主键。 |
| `search_fields` | `autocomplete` 远程搜索时目标资源参与搜索的字段。 |
| `limit` | 关联选项加载数量，默认 `100`。 |

如果字段没有显式配置 `rules`，内置页面会对“非空、无默认值、可编辑、非布尔”的字段自动生成必填规则。

### 控件类型

| `widget` | 适用场景 |
| --- | --- |
| `input` | 普通文本输入。 |
| `textarea` | 长文本字段，例如正文、描述、提示词。 |
| `switch` | 布尔字段。未配置时 bool 字段自动使用它。 |
| `number` | 整数或浮点数字段。未配置时 int/float 字段自动使用它。 |
| `select` | 固定选项、枚举字段、普通关联下拉。 |
| `autocomplete` | 远程搜索关联资源，适合数据量较大的作者、用户等字段。 |
| `date` | 日期字段。 |
| `datetime` | 日期时间字段。 |
| `json` | JSON 对象或数组，表单中以 textarea 编辑，保存前会解析为 JSON。 |

未显式声明 `widget` 时，前端会按字段类型自动选择：`choices` 使用 `select`，bool 使用 `switch`，数字使用 `number`，date/datetime 使用日期控件，dict/list 使用 `json`。

`json` 字段示例：

```python
admin.register(
    Agent,
    list_display=("id", "code", "name", "model", "created_at"),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("基础信息", {"fields": ("code", "name", "description", "model")}),
        ("提示词", {"fields": ("prompt",)}),
        ("能力配置", {"fields": ("setting", "tools", "parameters")}),
    ),
    config_meta={
        "icon": "fa-solid fa-robot",
        "fields": {
            "prompt": {"widget": "textarea", "table_hidden": True},
            "setting": {"widget": "json", "table_hidden": True},
            "tools": {"widget": "json", "table_hidden": True},
            "parameters": {"widget": "json", "table_hidden": True},
        },
    },
)
```

### 选项和枚举

`choices` 支持普通 list，也支持带标签样式的 dict：

```python
"status": {
    "choices": [
        {"label": "启用", "value": "active", "type": "success"},
        {"label": "禁用", "value": "disabled", "type": "info"},
    ]
}
```

未显式声明 `widget` 时，带有 `choices` 的字段会自动使用 `select`。SQLAlchemy Enum 字段会自动生成 choices；如果需要中文标签或标签颜色，建议显式配置 `choices`。

### 关联选择

关联字段的 `widget="select"` 和 `widget="autocomplete"` 会读取同级配置：

- `resource`：选项来源资源，比如 `users`
- `label_field`：选项展示字段，比如 `name`
- `value_field`：选项值字段，默认使用目标资源主键
- `search_fields`：远程搜索时使用的目标资源字段
- `limit`：选项加载数量，默认 `100`

`widget="autocomplete"` 会在输入时通过目标资源列表接口远程搜索：

```python
"author_id": {
    "widget": "autocomplete",
    "resource": "users",
    "label_field": "name",
    "search_fields": ("name", "email"),
    "placeholder": "请选择作者",
}
```

### 查询、排序和导出

- `search_fields`：顶部搜索框会向列表接口提交 `search` 参数。
- `list_filter`：查询区筛选字段。日期/时间字段会提交 `{field}__gte` 和 `{field}__lte`。
- `ordering_fields`：控制哪些表头允许排序。
- CSV 导出复用当前筛选和排序，默认最多导出 `10000` 条，可通过 `export_limit` 调小。

### 列表编辑

`list_editable` 用于声明列表页可直接编辑的真实模型字段。字段必须同时出现在 `list_display` 中，不能是主键、只读字段、隐藏字段或 `display_methods` 计算列。前端会在表格里记录本页草稿，点击“保存本页修改”后统一提交变更字段：

```python
admin.register(
    User,
    list_display=("id", "name", "email", "is_active"),
    list_editable=("is_active",),
)
```

### 计算列

`display_methods` 用于声明列表/详情里的只读计算列，适合展示状态文本、统计值或由多字段组合出的摘要。handler 必须是同步函数，可以接收 `obj`、`row` 或 `model_admin` 参数：

```python
def user_status_text(*, row):
    return "启用" if row.get("is_active") else "停用"

admin.register(
    User,
    list_display=("id", "name", "is_active", "status_text"),
    display_methods={
        "status_text": {
            "label": "状态文本",
            "handler": user_status_text,
            "width": 100,
        },
    },
)
```

### 自定义动作

自定义动作使用 `AdminAction` 声明，可用于批量动作或行级动作：

```python
from sqlalchemy import update

async def activate_users(*, session, pks):
    await session.execute(
        update(User).where(User.id.in_(pks)).values(is_active=True)
    )
    return {"message": f"已启用 {len(pks)} 个用户"}

async def deactivate_user(*, session, pk):
    await session.execute(update(User).where(User.id == pk).values(is_active=False))
    return {"message": "已停用用户"}

admin.register(
    User,
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
)
```

`scope` 可选 `bulk`、`row`、`both`。批量动作 handler 通常接收 `session` 和 `pks`；行级动作 handler 通常接收 `session` 和 `pk`。`variant` 会映射到 Element Plus 按钮类型。

### Admin 权限和动作开关

可以通过 `allowed_actions` 控制某个 admin 资源启用哪些基础动作：

```python
admin.register(
    User,
    allowed_actions=("list", "retrieve"),
)
```

也可以通过 `permission_classes` 和 `authentication_classes` 为某个资源覆盖默认认证和权限。

## Schema 自动生成

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
