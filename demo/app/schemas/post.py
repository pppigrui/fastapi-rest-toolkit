from src.fastapi_rest_toolkit.utils import sqlalchemy_model_to_pydantic
from app.models.post import Post
from app.models.user import User

UserRead = sqlalchemy_model_to_pydantic(User, name="UserRead")
UserCreate = sqlalchemy_model_to_pydantic(User, name="UserCreate")
UserUpdate = sqlalchemy_model_to_pydantic(User, name="UserUpdate")

    
PostRead = sqlalchemy_model_to_pydantic(Post, name="PostRead")
PostCreate = sqlalchemy_model_to_pydantic(Post, name="PostCreate")
PostUpdate = sqlalchemy_model_to_pydantic(Post, name="PostUpdate")
