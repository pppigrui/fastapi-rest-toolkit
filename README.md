# FastAPI REST Toolkit

类 Django REST Framework 风格的 FastAPI 工具包，提供简洁优雅的方式来构建 RESTful API。

## 特性

- **ViewSet**: 类似 DRF 的 ViewSet，支持 CRUD 操作
- **Router**: 自动路由注册，简化路由配置
- **权限系统**: 灵活的权限控制（AllowAny、IsAuthenticated、IsAdmin）
- **过滤器**: 支持搜索、排序、CRUD Plus 过滤
- **节流**: 内置限流机制，支持 Redis 存储
- **分页**: LimitOffset 分页支持

## 安装

```bash
pip install fastapi-rest-toolkit
```

如需使用 Redis 节流功能：

```bash
pip install fastapi-rest-toolkit[redis]
```

或安装所有可选依赖：

```bash
pip install fastapi-rest-toolkit[all]
```

## 快速开始

### 基本使用

```python
from fastapi import FastAPI
from fastapi_rest_toolkit import DefaultRouter, ViewSet, CRUDService
from pydantic import BaseModel

app = FastAPI()
router = DefaultRouter()

# 定义模型
class User(BaseModel):
    id: int
    name: str
    email: str

# 定义服务
class UserService(CRUDService):
    pass

# 定义 ViewSet
class UserViewSet(ViewSet):
    service_class = UserService

# 注册路由
router.register("/users", UserViewSet)
app.include_router(router)
```

### 权限控制

```python
from fastapi_rest_toolkit import ViewSet, IsAuthenticated

class ProtectedViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
```

### 过滤和搜索

```python
from fastapi_rest_toolkit import (
    ViewSet,
    SearchFilterBackend,
    OrderingFilterBackend,
)

class UserViewSet(ViewSet):
    filter_backends = [
        SearchFilterBackend,
        OrderingFilterBackend,
    ]
    search_fields = ["name", "email"]
    ordering_fields = ["id", "name", "created_at"]
```

### 节流

```python
from fastapi_rest_toolkit import ViewSet, AnonRateThrottle

class UserViewSet(ViewSet):
    throttle_classes = [AnonRateThrottle]
    throttle_rate = "100/hour"
```

## 组件

### ViewSet
提供标准的 CRUD 操作接口：
- `list()` - 获取列表
- `retrieve()` - 获取单个对象
- `create()` - 创建对象
- `update()` - 更新对象
- `destroy()` - 删除对象

### 权限类
- `AllowAny` - 允许所有访问
- `IsAuthenticated` - 需要认证
- `IsAdmin` - 需要管理员权限
- `BasePermission` - 自定义权限基类

### 过滤器
- `SearchFilterBackend` - 搜索过滤
- `OrderingFilterBackend` - 排序
- `CRUDPlusFilterBackend` - CRUD Plus 过滤

### 节流类
- `SimpleRateThrottle` - 简单限流
- `AnonRateThrottle` - 匿名用户限流
- `AsyncRedisSimpleRateThrottle` - 基于 Redis 的异步限流

## License

MIT License
