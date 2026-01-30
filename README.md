# FastAPI REST Toolkit

类 Django REST Framework 风格的 FastAPI 工具包，提供简洁优雅的方式来构建 RESTful API。

## 特性

- **ViewSet**: 类似 DRF 的 ViewSet，支持 CRUD 操作
- **Router**: 自动路由注册，简化路由配置
- **权限系统**: 灵活的权限控制（AllowAny、IsAuthenticated、IsAdmin）
- **过滤器**: 支持搜索、排序、CRUD Plus 过滤
- **节流**: 内置限流机制，支持 Redis 存储
- **Schema 工具**: 从 SQLAlchemy 模型自动生成 Pydantic Schema

## 安装

```bash
pip install fastapi-rest-toolkit
```

## 快速开始

### 完整示例

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func

from fastapi_rest_toolkit import DefaultRouter, ViewSet, CRUDService
from fastapi_rest_toolkit.permissions import IsAuthenticated, AllowAny
from fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from sqlalchemy_crud_plus import CRUDPlus
from app.db.redis import redis_client

# 1. 定义 SQLAlchemy 模型
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# 2. 定义 Schema（手动或自动生成）
from pydantic import BaseModel

class UserRead(BaseModel):
    id: int
    email: str
    name: str

class UserCreate(BaseModel):
    email: str
    name: str

class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None

# 3. 定义 ViewSet
class UserViewSet(ViewSet):
    read_schema = UserRead
    create_schema = UserCreate
    update_schema = UserUpdate

    # 权限配置
    permission_classes = (AllowAny, IsAuthenticated)

    # 搜索和排序
    search_fields = ("email", "name")
    ordering_fields = ("id", "email", "name", "created_at")

    # 节流配置
    throttle_classes = (AsyncRedisSimpleRateThrottle(redis=redis_client),)

    def __init__(self):
        user_crud = CRUDPlus(User)
        self.service = CRUDService(crud=user_crud, model=User)

# 4. 创建数据库会话
DATABASE_URL = "sqlite+aiosqlite:///./app.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with async_session() as session:
        yield session

# 5. 注册路由
app = FastAPI()
router = DefaultRouter()

router.register(
    "users",
    UserViewSet,
    get_session=get_session,
    get_user=get_current_user,  # 可选的认证依赖
    tags=["users"],
    pk_type=int,
)

app.include_router(router.router, prefix="/api")
```

### 自动生成 Schema

使用工具函数从 SQLAlchemy 模型自动生成 Pydantic Schema：

```python
from fastapi_rest_toolkit.utils import sqlalchemy_model_to_pydantic
from app.models.user import User

# 自动生成 Schema
UserRead = sqlalchemy_model_to_pydantic(User, name="UserRead")
UserCreate = sqlalchemy_model_to_pydantic(User, name="UserCreate", exclude={"id"})
UserUpdate = sqlalchemy_model_to_pydantic(User, name="UserUpdate", optional=True)
```

### 关联数据加载

支持加载关联数据（使用 selectinload）：

```python
class UserViewSet(ViewSet):
    load_strategies = ("posts",)  # 自动加载 posts 关联
```

### 权限控制

```python
from fastapi_rest_toolkit.permissions import AllowAny, IsAuthenticated, IsAdmin

class ProtectedViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)  # 需要登录

class AdminViewSet(ViewSet):
    permission_classes = (IsAdmin,)  # 需要管理员权限
```

### 搜索和排序

```python
class UserViewSet(ViewSet):
    # 支持搜索的字段
    search_fields = ("name", "email")

    # 支持排序的字段
    ordering_fields = ("id", "name", "created_at")
```

**API 使用示例：**

```bash
# 搜索
GET /api/users?search=john

# 排序
GET /api/users?ordering=-created_at

# 组合使用
GET /api/users?search=john&ordering=name
```

### 节流配置

```python
from fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from app.db.redis import redis_client

class UserViewSet(ViewSet):
    throttle_classes = (AsyncRedisSimpleRateThrottle(
        redis=redis_client,
        rate="100/hour"  # 可选，默认 100/hour
    ),)
```

### 异常处理

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """处理数据库完整性约束错误"""
    error_message = str(exc.orig)

    if "UNIQUE constraint failed" in error_message:
        parts = error_message.split(":")
        if len(parts) > 1:
            constraint_info = parts[1].strip()
            field = constraint_info.split(".")[-1] if "." in constraint_info else constraint_info
            detail = f"{field} 已存在"
    else:
        detail = error_message

    return JSONResponse(
        status_code=400,
        content={"detail": detail, "error_type": "integrity_error"}
    )

# 注册异常处理器
app.add_exception_handler(IntegrityError, integrity_error_handler)
```

## 组件说明

### ViewSet

提供标准的 CRUD 操作接口：

| 方法 | 路由 | 说明 |
|------|------|------|
| `list()` | `GET /api/users` | 获取列表（支持搜索、排序、分页） |
| `retrieve()` | `GET /api/users/{id}` | 获取单个对象 |
| `create()` | `POST /api/users` | 创建对象 |
| `update()` | `PUT/PATCH /api/users/{id}` | 更新对象 |
| `destroy()` | `DELETE /api/users/{id}` | 删除对象 |

### 权限类

- `AllowAny` - 允许所有访问
- `IsAuthenticated` - 需要认证
- `IsAdmin` - 需要管理员权限
- `BasePermission` - 自定义权限基类

### 过滤器

- `SearchFilterBackend` - 搜索过滤（使用 `search` 查询参数）
- `OrderingFilterBackend` - 排序（使用 `ordering` 查询参数）
- `CRUDPlusFilterBackend` - CRUD Plus 过滤

### 节流类

- `SimpleRateThrottle` - 简单限流（内存存储）
- `AnonRateThrottle` - 匿名用户限流
- `AsyncRedisSimpleRateThrottle` - 基于 Redis 的异步限流

### 工具函数

- `sqlalchemy_model_to_pydantic()` - 从 SQLAlchemy 模型生成 Pydantic Schema

## License

MIT License
