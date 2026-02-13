# FastAPI REST Toolkit

A Django REST Framework style toolkit for FastAPI, providing a clean and elegant way to build RESTful APIs.

## Features

- **ViewSet**: DRF-like ViewSet with full CRUD operations support
- **Router**: Automatic route registration, simplified routing configuration
- **Authentication System**: Flexible authentication mechanisms (Bearer Token, etc.)
- **Permission System**: Flexible permission control (AllowAny, IsAuthenticated, IsAdmin)
- **Filters**: Support for search, ordering, and CRUD Plus filtering
- **Throttling**: Built-in rate limiting with Redis storage support
- **Pagination**: Built-in LimitOffset pagination
- **Relation Loading**: Support for SQLAlchemy relationship data preloading
- **Schema Tools**: Automatically generate Pydantic Schemas from SQLAlchemy models

## Installation

```bash
pip install fastapi-rest-toolkit
```

Or install the full version with Redis dependencies:

```bash
pip install fastapi-rest-toolkit[all]
```

## Quick Start

### Complete Example

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, func

from fastapi_rest_toolkit import (
    DefaultRouter,
    ViewSet,
    CRUDService,
    AllowAny,
    IsAuthenticated,
    AsyncRedisSimpleRateThrottle,
)
from sqlalchemy_crud_plus import CRUDPlus
from app.db.redis import redis_client

# 1. Define SQLAlchemy model
class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# 2. Define Schemas (manually or auto-generated)
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

# 3. Define ViewSet
class UserViewSet(ViewSet):
    # read_schema = UserRead
    # create_schema = UserCreate
    # update_schema = UserUpdate
    model = User  # only define model for sqlalchemy
    # Permission configuration
    permission_classes = (AllowAny, IsAuthenticated)

    # Search and ordering
    search_fields = ("email", "name")
    ordering_fields = ("id", "email", "name", "created_at")

    # Throttle configuration
    throttle_classes = (AsyncRedisSimpleRateThrottle(redis=redis_client),)

    def __init__(self):
        user_crud = CRUDPlus(User)
        self.service = CRUDService(crud=user_crud, model=User)

# 4. Create database session
DATABASE_URL = "sqlite+aiosqlite:///./app.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with async_session() as session:
        yield session

# 5. Register routes
app = FastAPI()
router = DefaultRouter()

router.register(
    "users",
    UserViewSet,
    get_session=get_session,
    tags=["users"],
)

app.include_router(router.router, prefix="/api")
```

### Authentication System

Support custom authentication classes by extending `BaseAuthentication`:

```python
from fastapi import HTTPException, status
from fastapi_rest_toolkit.authentication import BearerAuthentication
from fastapi_rest_toolkit.request import FRFRequest
from fastapi_rest_toolkit.contextvar import session_var

class UserAuthentication(BearerAuthentication):
    async def authenticate(self, request: FRFRequest) -> tuple[Any, Any]:
        session = session_var.get()
        token = self.get_token(request)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication"
            )

        # Verify token and get user
        user = await self.verify_token(token, session)
        return user, token

# Use in ViewSet
class UserViewSet(ViewSet):
    authentication_classes = (UserAuthentication,)
    permission_classes = (IsAuthenticated,)
```

### Auto-generate Schemas

Use utility functions to automatically generate Pydantic Schemas from SQLAlchemy models:

```python
from fastapi_rest_toolkit.utils import sqlalchemy_model_to_pydantic
from app.models.user import User

# Auto-generate schemas
UserRead = sqlalchemy_model_to_pydantic(User, name="UserRead")
UserCreate = sqlalchemy_model_to_pydantic(User, name="UserCreate", exclude={"id"})
UserUpdate = sqlalchemy_model_to_pydantic(User, name="UserUpdate", optional=True)
```

### Relationship Data Loading

Support loading related data (using selectinload):

```python
class UserViewSet(ViewSet):
    load_strategies = ("posts",)  # Auto-load posts relationship
```

### Permission Control

```python
from fastapi_rest_toolkit import AllowAny, IsAuthenticated, IsAdmin

class ProtectedViewSet(ViewSet):
    permission_classes = (IsAuthenticated,)  # Requires login

class AdminViewSet(ViewSet):
    permission_classes = (IsAdmin,)  # Requires admin privileges
```

**Custom Permission Class:**

```python
from fastapi_rest_toolkit.permissions import BasePermission
from fastapi_rest_toolkit.request import FRFRequest

class IsOwner(BasePermission):
    async def has_permission(self, request: FRFRequest, viewset) -> bool:
        return request.user and request.user.id == int(request.path_params["id"])
```

### Pagination

Built-in `LimitOffsetPagination` support:

```python
from fastapi_rest_toolkit import ViewSet, LimitOffsetPagination

class CustomPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50

class UserViewSet(ViewSet):
    pagination = CustomPagination()
```

**API Usage Example:**

```bash
GET /api/users?limit=10&offset=0
```

### Search and Ordering

```python
class UserViewSet(ViewSet):
    # Searchable fields
    search_fields = ("name", "email")

    # Orderable fields
    ordering_fields = ("id", "name", "created_at")
```

**API Usage Example:**

```bash
# Search
GET /api/users?search=john

# Order
GET /api/users?ordering=-created_at

# Combined
GET /api/users?search=john&ordering=name
```

### Throttle Configuration

```python
from fastapi_rest_toolkit.throttle import AsyncRedisSimpleRateThrottle
from app.db.redis import redis_client

class UserViewSet(ViewSet):
    throttle_classes = (AsyncRedisSimpleRateThrottle(
        redis=redis_client,
        rate="100/hour"  # Optional, defaults to 100/hour
    ),)
```

**Available Throttle Classes:**

- `SimpleRateThrottle` - Simple rate limiting (in-memory storage)
- `AnonRateThrottle` - Anonymous user rate limiting
- `AsyncRedisSimpleRateThrottle` - Async rate limiting based on Redis

### Exception Handling

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity constraint errors"""
    error_message = str(exc.orig)

    if "UNIQUE constraint failed" in error_message:
        parts = error_message.split(":")
        if len(parts) > 1:
            constraint_info = parts[1].strip()
            field = constraint_info.split(".")[-1] if "." in constraint_info else constraint_info
            detail = f"{field} already exists"
    else:
        detail = error_message

    return JSONResponse(
        status_code=400,
        content={"detail": detail, "error_type": "integrity_error"}
    )

# Register exception handler
app.add_exception_handler(IntegrityError, integrity_error_handler)
```

### Custom Method Behavior

Customize behavior by overriding methods:

```python
class UserViewSet(ViewSet):
    async def create(self, request: FRFRequest):
        # Custom create logic
        data = await request.json()
        # ... custom handling
        return await super().create(request)

    async def destroy(self, request: FRFRequest, id: int):
        # Custom delete logic
        # ... check permissions, etc.
        return await super().destroy(request, id)
```

## Component Documentation

### ViewSet

Provides standard CRUD operation interfaces:

| Method | Route | Description |
|--------|-------|-------------|
| `list()` | `GET /api/users` | Get list (supports search, ordering, pagination) |
| `retrieve()` | `GET /api/users/{id}` | Get single object |
| `create()` | `POST /api/users` | Create object |
| `update()` | `PUT/PATCH /api/users/{id}` | Update object |
| `destroy()` | `DELETE /api/users/{id}` | Delete object |

**ViewSet Configuration Options:**

```python
class ViewSet:
    # Schema configuration
    read_schema: Type[BaseModel]      # Schema for reading data
    create_schema: Type[BaseModel]    # Schema for creating data
    update_schema: Type[BaseModel]    # Schema for updating data

    # Authentication and permissions
    authentication_classes: Sequence[Type[BaseAuthentication]]  # Authentication classes
    permission_classes: Sequence[Type[BasePermission]]          # Permission classes

    # Filtering and ordering
    search_fields: Sequence[str]       # Searchable fields
    ordering_fields: Sequence[str]     # Orderable fields
    filter_backends: Sequence          # Filter backends

    # Pagination and throttling
    pagination: LimitOffsetPagination  # Pagination configuration
    throttle_classes: Sequence[Type[BaseThrottle]]  # Throttle classes
    throttle_scope: str                # Throttle scope

    # Relationship loading
    load_strategies: Sequence[str]     # Preloaded relationship fields
    join_conditions: Any               # Join conditions

    # Allowed HTTP methods
    allowed_methods: Sequence[str]     # Defaults to all CRUD methods
```

### Authentication Classes

- `BaseAuthentication` - Base authentication class
- `BearerAuthentication` - Base Bearer Token authentication class

**Custom Authentication:**

```python
from fastapi_rest_toolkit.authentication import BaseAuthentication
from fastapi_rest_toolkit.request import FRFRequest

class CustomAuth(BaseAuthentication):
    async def authenticate(self, request: FRFRequest) -> tuple[Any, Any]:
        # Return (user, auth) or (None, None)
        pass
```

### Permission Classes

- `AllowAny` - Allow all access
- `IsAuthenticated` - Requires authentication
- `IsAdmin` - Requires admin privileges
- `BasePermission` - Custom permission base class

### Filters

- `SearchFilterBackend` - Search filtering (using `search` query parameter)
- `OrderingFilterBackend` - Ordering (using `ordering` query parameter)
- `CRUDPlusFilterBackend` - CRUD Plus filtering

### Throttle Classes

- `SimpleRateThrottle` - Simple rate limiting (in-memory storage)
- `AnonRateThrottle` - Anonymous user rate limiting
- `AsyncRedisSimpleRateThrottle` - Async rate limiting based on Redis

### Router

`DefaultRouter` automatically registers routes for ViewSets:

```python
router = DefaultRouter()
router.register(
    prefix="users",           # URL prefix
    viewset=UserViewSet,      # ViewSet class
    get_session=get_session,  # Database session getter function
    tags=["users"],           # OpenAPI tags
)
app.include_router(router.router, prefix="/api")
```

### Utility Functions

- `sqlalchemy_model_to_pydantic()` - Generate Pydantic Schema from SQLAlchemy model

## Complete Demo

See the [demo](./demo/) directory for complete usage examples, including:

- Database model definitions
- JWT authentication implementation
- Redis throttle configuration
- Exception handling
- Multiple ViewSet implementations

Run the example:

```bash
cd demo
uvicorn main:app --reload
```

Access API documentation at: http://127.0.0.1:8000/docs

## License

MIT License
