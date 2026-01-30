from fastapi_rest_toolkit.utils import sqlalchemy_model_to_pydantic

from app.models.user import User


UserRead = sqlalchemy_model_to_pydantic(User, name="UserRead")
UserCreate = sqlalchemy_model_to_pydantic(User, name="UserCreate")
UserUpdate = sqlalchemy_model_to_pydantic(User, name="UserUpdate")
