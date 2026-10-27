from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import token_digest
from app.database.db import AuthToken, User, get_db


def current_user_optional(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    """None for guests. A token that is present but invalid or expired is an error, never a silent guest."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid authorization header")
    row = db.get(AuthToken, token_digest(token))
    if row is not None:
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires > datetime.now(timezone.utc):
            user = db.get(User, row.user_id)
            if user is not None:
                return user
    raise HTTPException(401, "Invalid or expired token")


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(401, "Sign in required")
    return user
