from datetime import datetime, timezone
from typing import Any, Dict

from jose import JWTError, jwt
from fastapi import HTTPException, status

# ⚠️ Demo only: move these to env/config in production
JWT_SECRET_KEY = "CHANGE_ME"
JWT_ALGORITHM = "HS256"


def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    exp = payload.get("exp")
    if exp is not None:
        now = datetime.now(timezone.utc).timestamp()
        if float(exp) < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )

    return payload


def encode_jwt(payload: Dict[str, Any]) -> str:
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
