from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy_crud_plus import CRUDPlus

from app.auth.jwt import decode_jwt
from app.db.session import get_session
from app.models.user import User

bearer = HTTPBearer(auto_error=False)  # allow anonymous; permissions decide

user_crud = CRUDPlus(User)


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    session=Depends(get_session),
) -> Optional[User]:
    if creds is None:
        return None

    if creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme"
        )

    payload = decode_jwt(creds.credentials)

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject"
        )

    user = await user_crud.select_model(session, pk=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user
