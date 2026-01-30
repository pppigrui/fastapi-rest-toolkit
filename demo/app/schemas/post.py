from src.fastapi_rest_toolkit.utils import sqlalchemy_model_to_pydantic
from app.models.post import Post
    
PostRead = sqlalchemy_model_to_pydantic(Post, name="PostRead")
PostCreate = sqlalchemy_model_to_pydantic(Post, name="PostCreate")
PostUpdate = sqlalchemy_model_to_pydantic(Post, name="PostUpdate")
