from typing import Any
from fastapi import HTTPException, status
from demo.app.auth.deps import user_crud
from demo.app.auth.jwt import decode_jwt
from src.fastapi_rest_toolkit.authentication import BearerAuthentication
from src.fastapi_rest_toolkit.contextvar import session_var
from src.fastapi_rest_toolkit.request import FRFRequest


class UserAuthentication(BearerAuthentication):
    async def authenticate(self, request: FRFRequest) -> tuple[Any, Any]:
        session = session_var.get()
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found"
            )
        token = self.get_token(request)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme"
            )

        payload = decode_jwt(token)
        sub = payload.get("sub")  # user_id stored in token
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

        return user, token
