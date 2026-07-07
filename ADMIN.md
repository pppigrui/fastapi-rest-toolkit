# Admin 管理后台配置指南

本文档集中说明 `fastapi_rest_toolkit` 内置 admin 的所有常用配置。admin 的定位是一个 Django-admin-like 的轻量后台：基于 SQLAlchemy model 自动生成 CRUD 接口、元数据接口和本地 Vue 3 + Element Plus 管理页面。

## 1. 快速接入

在 FastAPI 应用启动文件中创建 `AdminSite`，注册 SQLAlchemy model，然后挂载 `admin.router`：

```python
from fastapi import FastAPI

from fastapi_rest_toolkit import AdminSite
from app.db.session import get_session
from app.models.user import UserModel
from app.models.role import RoleModel, UserRoleModel

app = FastAPI()

admin = AdminSite(get_session=get_session, title="管理后台")

admin.register(UserModel, label="用户管理", group="权限管理")
admin.register(RoleModel, label="角色管理", group="权限管理")
admin.register(UserRoleModel, label="用户角色关联", group="权限管理")

app.include_router(admin.router, prefix="/admin")
```

启动后访问：

```text
http://127.0.0.1:8000/admin
```

自动生成的接口在 `/admin/api` 下：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/admin/api/meta` | 后台标题、菜单、模型、字段和动作元数据 |
| `GET` | `/admin/api/{resource}` | 列表 |
| `POST` | `/admin/api/{resource}` | 新增 |
| `GET` | `/admin/api/{resource}/{pk}` | 详情 |
| `PUT` | `/admin/api/{resource}/{pk}` | 修改 |
| `DELETE` | `/admin/api/{resource}/{pk}` | 删除 |
| `POST` | `/admin/api/{resource}/batch-delete` | 批量删除 |
| `GET` | `/admin/api/{resource}/export.csv` | 按当前筛选和排序导出 CSV |
| `POST` | `/admin/api/{resource}/actions/{action}` | 批量自定义动作 |
| `POST` | `/admin/api/{resource}/{pk}/actions/{action}` | 行级自定义动作 |

## 2. `AdminSite`

`AdminSite` 负责管理后台路由、模型注册、元数据接口、静态资源和每个模型的 CRUD 路由。

常用写法：

```python
admin = AdminSite(
    get_session=get_session,
    title="管理后台",
)
```

核心参数：

| 参数 | 说明 |
| --- | --- |
| `get_session` | 必填。FastAPI dependency，返回 SQLAlchemy `AsyncSession`。 |
| `title` | 管理后台标题，会显示在页面左上角和 meta 接口中。 |
| `permission_classes` | 全局权限类。单个资源可以在 `admin.register()` 中覆盖。 |
| `authentication_classes` | 全局认证类。单个资源可以在 `admin.register()` 中覆盖。 |

## 3. `admin.register()` 参数总览

`admin.register()` 是 admin 配置的主要入口。它把一个 SQLAlchemy model 注册成后台资源。

```python
admin.register(
    UserModel,
    label="用户管理",
    group="权限管理",
    resource="users",
    list_display=("id", "username", "email", "is_active", "created_at"),
    search_fields=("username", "email"),
    list_filter=("is_active", "created_at"),
    ordering_fields=("id", "username", "email", "created_at"),
    readonly_fields=("id", "created_at", "updated_at"),
    allowed_actions=("list", "retrieve", "create", "update", "destroy"),
    fieldsets=(
        ("基础信息", {"fields": ("username", "email", "display_name")}),
        ("状态", {"fields": ("is_active", "is_superuser")}),
    ),
    list_editable=("is_active",),
    config_meta={
        "icon": "fa-solid fa-user",
        "fields": {
            "is_active": {"widget": "switch", "width": 120},
        },
    },
)
```

完整参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `model` | 必填 | SQLAlchemy model。 |
| `label` | `model.__name__` | 菜单、标题、抽屉标题中显示的名称。 |
| `group` | `"管理"` | 左侧菜单分组。 |
| `resource` | `model.__tablename__` | API 和前端资源名，例如 `users`。关联选择字段会引用它。 |
| `list_display` | 全部表字段 | 列表展示字段，可包含真实字段和 `display_methods` 计算列。 |
| `search_fields` | `()` | 顶部搜索框参与模糊搜索的真实字段。 |
| `list_filter` | `()` | 查询区筛选字段。 |
| `ordering_fields` | `list_display` 中的真实字段 | 允许点击表头排序的字段。 |
| `readonly_fields` | `()` | 创建/编辑表单不提交的字段。常用于 `id`、`created_at`。 |
| `allowed_actions` | `("list", "retrieve", "create", "update", "destroy")` | 开启的基础动作。 |
| `fieldsets` | `None` | 创建、编辑、详情抽屉的字段分组。 |
| `actions` | `()` | 自定义批量动作或行级动作。 |
| `display_methods` | `None` | 只读计算列。 |
| `list_editable` | `()` | 列表页可直接编辑的字段。 |
| `config_meta` | `None` | 前端配置，主要包含 `icon` 和 `fields`。 |
| `permission_classes` | `None` | 当前资源专用权限类。 |
| `authentication_classes` | `None` | 当前资源专用认证类。 |

## 4. SQLAlchemy model 字段约定

字段显示名优先读取 SQLAlchemy column 的 `info["name"]`：

```python
username = mapped_column(String(64), info={"name": "用户名"})
```

如果没有 `info["name"]`，页面会显示 Python 字段名，例如 `username`。

JSON 字段如果需要指定 Python 类型，可以使用 `info["python_type"]`：

```python
tools = mapped_column(
    JSON,
    nullable=True,
    info={"name": "工具列表", "python_type": list},
)
```

主键处理规则：

- 单列、非外键、自动生成主键会被 admin 视为自动字段，创建表单不显示。
- 联合主键、外键主键不会被自动视为只读，适合 `user_id + role_id`、`post_id + tag_id` 这类关联表新增场景。
- 当前详情、编辑、删除接口仍是单主键 URL 设计；联合主键关联表建议先开放 `list/create`。

## 5. `fieldsets` 字段分组

`fieldsets` 用于声明创建、编辑和详情抽屉中的字段分组：

```python
fieldsets=(
    ("基础信息", {"fields": ("username", "email", "display_name")}),
    (
        "状态权限",
        {
            "fields": ("is_active", "is_superuser"),
            "description": "控制账号是否可登录，以及是否拥有最高权限。",
        },
    ),
)
```

支持配置：

| 配置 | 说明 |
| --- | --- |
| `fields` | 分组字段名列表。 |
| `description` | 分组说明。 |
| `collapsible` | 是否可折叠，元数据支持。 |
| `default_collapsed` | 默认是否折叠，元数据支持。 |

未出现在 `fieldsets` 中的可见字段，会被放到“其他”分组。

## 6. `config_meta`

`config_meta` 是传给前端的配置容器。稳定顶层配置目前主要是：

| 配置 | 说明 |
| --- | --- |
| `icon` | 菜单图标 class，支持本地 Font Awesome，例如 `fa-solid fa-user`。 |
| `fields` | 字段级配置。 |

示例：

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

## 7. 字段级配置

字段级配置写在 `config_meta["fields"]` 下，key 是字段名或计算列名。

| 配置 | 说明 |
| --- | --- |
| `hidden` | 表格、表单、详情全部隐藏。 |
| `table_hidden` | 只在列表表格隐藏。 |
| `form_hidden` | 只在创建/编辑表单隐藏。 |
| `detail_hidden` | 只在详情视图隐藏。 |
| `placeholder` | 表单控件和查询控件的占位提示。 |
| `widget` | 控件类型，见下方控件表。 |
| `help_text` | 表单字段下方的辅助说明。 |
| `width` | 表格列宽，传给 Element Plus `el-table-column`。 |
| `rules` | Element Plus 表单校验规则。 |
| `choices` | 声明式选项，用于下拉、筛选和标签渲染。 |
| `resource` | 关联选择字段的目标资源名，例如 `users`。 |
| `label_field` | 关联选项显示字段，例如 `username`、`name`、`title`。 |
| `value_field` | 关联选项值字段；不传时使用目标资源主键。 |
| `search_fields` | `autocomplete` 远程搜索时目标资源参与搜索的字段。 |
| `limit` | 关联选项加载数量，默认 `100`。 |

如果字段没有显式配置 `rules`，前端会对“非空、无默认值、可编辑、非布尔”的字段自动生成必填规则。

## 8. 控件类型

| `widget` | 适用字段 |
| --- | --- |
| `input` | 普通文本。 |
| `textarea` | 长文本，例如简介、正文、描述、提示词。 |
| `switch` | 布尔字段。未配置时 bool 自动使用。 |
| `number` | int/float 数字字段。未配置时数字自动使用。 |
| `select` | 固定选项、枚举字段、小数据量关联选择。 |
| `autocomplete` | 远程搜索关联资源，适合用户、文章等较大数据集。 |
| `date` | 日期字段。 |
| `datetime` | 日期时间字段。 |
| `json` | JSON 对象或数组，以 textarea 编辑，提交前解析为 JSON。 |

自动推断规则：

- 有 `choices` 的字段默认使用 `select`。
- bool 使用 `switch`。
- int/float 使用 `number`。
- date/datetime 使用日期控件。
- dict/list 使用 `json`。
- 其他字段使用 `input`。

## 9. 选项和枚举

固定选项可以使用 `choices`：

```python
"status": {
    "widget": "select",
    "width": 120,
    "choices": [
        {"label": "草稿", "value": "draft", "type": "info"},
        {"label": "审核中", "value": "reviewing", "type": "warning"},
        {"label": "已发布", "value": "published", "type": "success"},
        {"label": "已归档", "value": "archived", "type": "info"},
    ],
}
```

`type` 会映射到 Element Plus tag 类型。SQLAlchemy Enum 字段会自动生成 choices；如果需要中文标签或颜色，建议显式配置。

## 10. 关联选择

普通关联下拉：

```python
"role_id": {
    "widget": "select",
    "resource": "roles",
    "label_field": "name",
    "value_field": "id",
    "placeholder": "请选择角色",
    "rules": [
        {"required": True, "message": "请选择角色", "trigger": "change"},
    ],
}
```

远程搜索关联：

```python
"author_id": {
    "widget": "autocomplete",
    "resource": "users",
    "label_field": "name",
    "value_field": "id",
    "search_fields": ("name", "email"),
    "placeholder": "请选择作者",
}
```

注意事项：

- `resource` 必须等于目标模型注册时的资源名。默认是目标表名，也可以由 `admin.register(..., resource="xxx")` 自定义。
- 如果目标资源使用默认主键 `id`，`value_field` 可以省略。
- `select` 首次打开表单时会加载前 `limit` 条，默认 `100`。
- `autocomplete` 会在输入关键词时调用目标资源列表接口。

## 11. 查询、排序和导出

`search_fields` 控制顶部搜索框：

```python
search_fields=("username", "email", "display_name")
```

`list_filter` 控制查询区：

```python
list_filter=("is_active", "role", "created_at")
```

字段表现：

- bool 字段显示是/否下拉。
- date/datetime 字段显示范围选择器。
- 有 `choices` 的字段显示选项下拉。
- 其他字段显示输入框。

`ordering_fields` 控制哪些表头允许排序：

```python
ordering_fields=("id", "username", "email", "created_at")
```

CSV 导出会复用当前筛选和排序，默认最多导出 `10000` 条。

## 12. 列表编辑

`list_editable` 用于在列表页直接编辑字段：

```python
admin.register(
    UserModel,
    list_display=("id", "username", "email", "is_active"),
    list_editable=("is_active",),
)
```

约束：

- 字段必须在 `list_display` 中。
- 必须是真实模型字段。
- 不能是主键。
- 不能在 `readonly_fields` 中。
- 不能被 `hidden` 或 `table_hidden` 隐藏。
- 不能是 `display_methods` 计算列。

## 13. 计算列 `display_methods`

计算列适合展示由多个字段推导出的只读值，例如状态文案、字数、摘要。

```python
def user_status_text(*, row):
    return "启用" if row.get("is_active") else "停用"


admin.register(
    UserModel,
    list_display=("id", "username", "is_active", "status_text"),
    display_methods={
        "status_text": {
            "label": "状态文本",
            "handler": user_status_text,
            "type": "str",
            "width": 100,
        },
    },
)
```

`display_methods` 支持两种写法：

```python
display_methods={
    "status_text": user_status_text,
}
```

或：

```python
display_methods={
    "status_text": {
        "label": "状态文本",
        "handler": user_status_text,
        "type": "str",
        "width": 100,
    },
}
```

handler 可以按需接收：

- `obj`：SQLAlchemy ORM 对象。
- `row`：已经序列化后的 dict。
- `model_admin`：当前 `ModelAdmin`。

## 14. 自定义动作 `AdminAction`

自定义动作适合批量启用、批量归档、重置状态、行级停用等场景。

```python
from sqlalchemy import update
from fastapi_rest_toolkit import AdminAction


async def activate_users(*, session, pks):
    await session.execute(
        update(UserModel).where(UserModel.id.in_(pks)).values(is_active=True)
    )
    return {"message": f"已启用 {len(pks)} 个用户"}


async def deactivate_user(*, session, pk):
    await session.execute(
        update(UserModel).where(UserModel.id == pk).values(is_active=False)
    )
    return {"message": "已停用用户"}


admin.register(
    UserModel,
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

`AdminAction` 参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `name` | 必填 | 动作名，用于接口路径。 |
| `label` | 必填 | 按钮文案。 |
| `handler` | 必填 | 同步或异步处理函数。 |
| `scope` | `"bulk"` | `bulk`、`row` 或 `both`。 |
| `confirmation` | `None` | 确认弹窗文案。 |
| `variant` | `"primary"` | Element Plus 按钮类型，例如 `success`、`warning`、`danger`。 |

handler 可接收的参数包括：

- `request`
- `session`
- `model_admin`
- `payload`
- `pk`
- `pks`

函数只需要声明自己用到的参数。

## 15. 基础动作开关

`allowed_actions` 控制内置 CRUD 能力：

```python
admin.register(
    AuditLogModel,
    label="审计日志",
    allowed_actions=("list", "retrieve"),
)
```

常见组合：

| 场景 | 配置 |
| --- | --- |
| 完整 CRUD | `("list", "retrieve", "create", "update", "destroy")` |
| 只读列表和详情 | `("list", "retrieve")` |
| 只允许列表 | `("list",)` |
| 联合主键关联表新增演示 | `("list", "create")` |

## 16. 常用表配置示例

### 16.1 用户表

模型示例：

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, info={"name": "用户名"}
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, info={"name": "密码哈希"}
    )
    display_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, info={"name": "显示名称"}
    )
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, info={"name": "邮箱"}
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, info={"name": "是否激活"}
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, info={"name": "是否超级用户"}
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, info={"name": "最后登录时间"}
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), info={"name": "创建时间"}
    )
```

admin 配置：

```python
def user_status_text(*, row):
    return "启用" if row.get("is_active") else "停用"


admin.register(
    UserModel,
    label="用户管理",
    group="权限管理",
    resource="users",
    list_display=(
        "id",
        "username",
        "display_name",
        "email",
        "is_active",
        "is_superuser",
        "status_text",
        "last_login_at",
        "created_at",
    ),
    list_editable=("is_active",),
    search_fields=("username", "display_name", "email"),
    list_filter=("is_active", "is_superuser", "last_login_at", "created_at"),
    ordering_fields=("id", "username", "email", "last_login_at", "created_at"),
    readonly_fields=("id", "created_at", "last_login_at"),
    fieldsets=(
        ("账号信息", {"fields": ("username", "password_hash", "display_name", "email")}),
        ("状态权限", {"fields": ("is_active", "is_superuser")}),
    ),
    display_methods={
        "status_text": {
            "label": "状态",
            "handler": user_status_text,
            "width": 90,
        },
    },
    config_meta={
        "icon": "fa-solid fa-user",
        "fields": {
            "username": {
                "placeholder": "请输入用户名",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请输入用户名", "trigger": "blur"},
                ],
            },
            "password_hash": {
                "table_hidden": True,
                "detail_hidden": True,
                "placeholder": "请输入密码哈希",
                "help_text": "示例配置直接保存 password_hash；真实项目通常应在业务层处理密码加密。",
                "rules": [
                    {"required": True, "message": "请输入密码哈希", "trigger": "blur"},
                ],
            },
            "email": {
                "placeholder": "请输入邮箱",
                "width": 220,
                "rules": [
                    {"type": "email", "message": "请输入正确的邮箱", "trigger": "blur"},
                ],
            },
            "is_active": {"widget": "switch", "width": 120},
            "is_superuser": {"widget": "switch", "width": 130},
            "last_login_at": {"widget": "datetime", "form_hidden": True, "width": 180},
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)
```

### 16.2 角色表

模型示例：

```python
from typing import Any

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, info={"name": "ID"})
    name: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, info={"name": "角色名"}
    )
    display_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, info={"name": "显示名称"}
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, info={"name": "描述"}
    )
    agents: Mapped[Any | None] = mapped_column(
        JSON, default=None, nullable=True, info={"name": "可访问的 Agent"}
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, info={"name": "是否激活"}
    )
```

admin 配置：

```python
admin.register(
    RoleModel,
    label="角色管理",
    group="权限管理",
    resource="roles",
    list_display=("id", "name", "display_name", "is_active", "description"),
    list_editable=("display_name", "is_active"),
    search_fields=("name", "display_name", "description"),
    list_filter=("is_active",),
    ordering_fields=("id", "name", "display_name"),
    readonly_fields=("id",),
    fieldsets=(
        ("基础信息", {"fields": ("name", "display_name", "description")}),
        ("权限范围", {"fields": ("agents", "is_active")}),
    ),
    config_meta={
        "icon": "fa-solid fa-user-shield",
        "fields": {
            "name": {
                "placeholder": "请输入唯一角色名，例如 admin",
                "width": 150,
                "rules": [
                    {"required": True, "message": "请输入角色名", "trigger": "blur"},
                ],
            },
            "display_name": {"placeholder": "请输入显示名称", "width": 150},
            "description": {
                "widget": "textarea",
                "placeholder": "请输入角色说明",
                "width": 220,
            },
            "agents": {
                "widget": "json",
                "table_hidden": True,
                "placeholder": "[\"chat\", \"search\"]",
                "help_text": "JSON 数组或对象，用于描述该角色可访问的 Agent。",
            },
            "is_active": {"widget": "switch", "width": 120},
        },
    },
)
```

### 16.3 用户角色关联表

SQLAlchemy 多对多关联表必须有主键。`user_id + role_id` 这种联合主键不要去掉，否则 SQLAlchemy 会报：

```text
Mapper could not assemble any primary key columns
```

模型示例：

```python
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRoleModel(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        info={"name": "用户 ID"},
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        info={"name": "角色 ID"},
    )
```

admin 配置：

```python
admin.register(
    UserRoleModel,
    label="用户角色关联",
    group="权限管理",
    resource="user_roles",
    list_display=("user_id", "role_id"),
    allowed_actions=("list", "create"),
    config_meta={
        "icon": "fa-solid fa-link",
        "fields": {
            "user_id": {
                "widget": "select",
                "resource": "users",
                "label_field": "username",
                "value_field": "id",
                "placeholder": "请选择用户",
                "width": 180,
                "rules": [
                    {"required": True, "message": "请选择用户", "trigger": "change"},
                ],
            },
            "role_id": {
                "widget": "select",
                "resource": "roles",
                "label_field": "name",
                "value_field": "id",
                "placeholder": "请选择角色",
                "width": 160,
                "rules": [
                    {"required": True, "message": "请选择角色", "trigger": "change"},
                ],
            },
        },
    },
)
```

如果 `UserModel` 或 `RoleModel` 注册时自定义了 `resource`，关联表里也要同步修改：

```python
admin.register(UserModel, label="用户管理", resource="auth_users")
admin.register(RoleModel, label="角色管理", resource="auth_roles")

admin.register(
    UserRoleModel,
    config_meta={
        "fields": {
            "user_id": {"resource": "auth_users", "label_field": "username"},
            "role_id": {"resource": "auth_roles", "label_field": "name"},
        }
    },
)
```

### 16.4 文章表

文章表适合演示枚举、作者关联、长文本、日期时间和列表编辑。

```python
admin.register(
    PostModel,
    label="文章管理",
    group="内容管理",
    resource="posts",
    list_display=(
        "id",
        "title",
        "author_id",
        "category",
        "status",
        "is_published",
        "view_count",
        "created_at",
    ),
    list_editable=("title", "status", "is_published"),
    search_fields=("title", "summary", "content", "category"),
    list_filter=("author_id", "category", "status", "is_published", "created_at"),
    ordering_fields=("id", "title", "view_count", "created_at"),
    readonly_fields=("id", "created_at"),
    fieldsets=(
        ("文章信息", {"fields": ("title", "author_id", "category", "status")}),
        ("发布控制", {"fields": ("is_published", "publish_date", "published_at")}),
        ("内容", {"fields": ("summary", "content")}),
        ("指标", {"fields": ("view_count",)}),
    ),
    config_meta={
        "icon": "fa-solid fa-file-lines",
        "fields": {
            "author_id": {
                "widget": "autocomplete",
                "resource": "users",
                "label_field": "username",
                "value_field": "id",
                "search_fields": ("username", "email"),
                "placeholder": "请选择作者",
                "width": 160,
                "rules": [
                    {"required": True, "message": "请选择作者", "trigger": "change"},
                ],
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
            "is_published": {"widget": "switch", "width": 120},
            "summary": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入摘要",
            },
            "content": {
                "widget": "textarea",
                "table_hidden": True,
                "placeholder": "请输入正文内容",
            },
            "publish_date": {"widget": "date", "width": 150},
            "published_at": {"widget": "datetime", "width": 180},
            "view_count": {"widget": "number", "width": 110},
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)
```

### 16.5 标签和文章标签关联表

标签表：

```python
admin.register(
    TagModel,
    label="标签管理",
    group="内容管理",
    resource="tags",
    list_display=("id", "name", "color"),
    list_editable=("name", "color"),
    search_fields=("name", "color"),
    ordering_fields=("id", "name"),
    readonly_fields=("id",),
    config_meta={
        "icon": "fa-solid fa-tags",
        "fields": {
            "name": {
                "placeholder": "请输入标签名",
                "width": 160,
                "rules": [
                    {"required": True, "message": "请输入标签名", "trigger": "blur"},
                ],
            },
            "color": {
                "placeholder": "例如 #409eff",
                "width": 130,
            },
        },
    },
)
```

文章标签关联表：

```python
admin.register(
    PostTagModel,
    label="文章标签关联",
    group="内容管理",
    resource="post_tags",
    list_display=("post_id", "tag_id"),
    allowed_actions=("list", "create"),
    config_meta={
        "icon": "fa-solid fa-link",
        "fields": {
            "post_id": {
                "widget": "select",
                "resource": "posts",
                "label_field": "title",
                "value_field": "id",
                "placeholder": "请选择文章",
                "width": 220,
                "rules": [
                    {"required": True, "message": "请选择文章", "trigger": "change"},
                ],
            },
            "tag_id": {
                "widget": "select",
                "resource": "tags",
                "label_field": "name",
                "value_field": "id",
                "placeholder": "请选择标签",
                "width": 160,
                "rules": [
                    {"required": True, "message": "请选择标签", "trigger": "change"},
                ],
            },
        },
    },
)
```

### 16.6 Agent 配置表

Agent 表适合演示 JSON、textarea、fieldsets 和隐藏列。

```python
admin.register(
    AgentModel,
    label="Agent 配置",
    group="AI",
    resource="agents",
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
            },
            "model": {
                "placeholder": "请输入模型名称",
                "width": 150,
            },
            "setting": {
                "widget": "json",
                "table_hidden": True,
                "placeholder": "{\n  \"enable_user_memory\": true\n}",
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
                "placeholder": "{\n  \"temperature\": 0.7\n}",
                "help_text": "JSON 对象，用于配置模型推理参数。",
            },
            "created_at": {"form_hidden": True, "width": 180},
        },
    },
)
```

## 17. 推荐配置习惯

- `id`、`created_at`、`updated_at` 通常放进 `readonly_fields`，并给时间字段配置 `form_hidden`。
- 常用筛选字段放进 `list_filter`，不要把太多长文本字段放进去。
- 长文本字段使用 `textarea`，并通常配置 `table_hidden`。
- JSON 字段使用 `widget="json"`，同时给出 `placeholder` 示例。
- 关系字段优先配置 `resource`、`label_field`、`value_field`，避免用户直接输入外键数字。
- 数据量小的关联用 `select`；数据量大的关联用 `autocomplete`。
- 纯关联表或联合主键表建议先配置 `allowed_actions=("list", "create")`。
- 对用户表中的密码字段，不建议直接暴露明文输入；如果当前模型只有 `password_hash`，请在字段说明中明确它保存的是哈希值。

## 18. 当前限制

- 联合主键模型可以用于新增，但详情、编辑、删除仍基于单主键 URL，建议关联表先只开放 `list/create`。
- 内置 admin 不处理密码加密、业务审计、复杂权限策略；这些应放在业务层或自定义动作中。
- 前端资源是本地静态文件，不依赖 CDN；不要在内置 admin 中引入 React、TypeScript 或构建步骤。
- `config_meta` 中未文档化的配置不保证长期稳定，稳定顶层 API 应优先放在 `admin.register()` 参数中。
