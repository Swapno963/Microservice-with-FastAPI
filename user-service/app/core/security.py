from typing import Optional, Union, Dict, Any
from jose import jwt
from app.core.config import settings


def verify_token(token: str, token_type: str) -> Optional[Dict[str, Any]]:
    """Verify a jwt token and return it's payload"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Check the token type
        if payload.get("type") != token_type:
            return None

        return payload

    except jwt.JWTError:
        return None
