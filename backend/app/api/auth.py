import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import hash_password, new_token, token_digest, verify_password
from app.database.db import AdaptiveDecision, AuthToken, ExerciseSession, User, get_db

router = APIRouter(prefix="/api")
TOKEN_DAYS = 30
AgeRange = Literal["", "<18", "18-30", "31-45", "46-60", "61-75", "75+"]
ALLOWED_PREFERENCES = {"audio_feedback": bool, "show_demo_data": bool}  # small, non-sensitive settings only


class Credentials(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,32}$")
    password: str = Field(min_length=8, max_length=128)


class RegisterIn(Credentials):
    age_range: AgeRange = ""
    goals: str = Field(default="", max_length=256)  # free text; do not enter medical details


class ProfilePatch(BaseModel):
    age_range: AgeRange | None = None
    goals: str | None = Field(default=None, max_length=256)
    preferences: dict[str, bool] | None = None


class UserOut(BaseModel):
    id: str
    username: str
    age_range: str | None
    goals: str | None
    preferences: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class AuthOut(BaseModel):
    token: str
    user: UserOut


def _issue_token(db: Session, user: User) -> str:
    token = new_token()
    db.add(AuthToken(token_digest=token_digest(token), user_id=user.id,
                     expires_at=datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)))
    db.commit()
    return token


@router.post("/auth/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> AuthOut:
    if db.scalar(select(User).where(User.username == body.username)) is not None:
        raise HTTPException(409, "Username already taken")
    user = User(username=body.username, password_hash=hash_password(body.password),
                age_range=body.age_range or None, goals=body.goals or None, preferences={})
    db.add(user)
    db.commit()
    return AuthOut(token=_issue_token(db, user), user=UserOut.model_validate(user))


MAX_FAILURES = 5
LOCKOUT_WINDOW_S = 300.0
_failures: dict[str, deque[float]] = {}
_now = time.monotonic  # replaceable in tests


def _lockout_key(username: str, request: Request) -> str:
    return f"{username.lower()}|{request.client.host if request.client else '?'}"


def _check_not_locked(key: str) -> None:
    """At most MAX_FAILURES failed sign-ins per username and address in LOCKOUT_WINDOW_S (counted for unknown usernames too,
    so the limit does not reveal which accounts exist). Even the correct password is refused while locked."""
    q = _failures.get(key)
    if not q:
        return
    now = _now()
    while q and now - q[0] > LOCKOUT_WINDOW_S:
        q.popleft()
    if len(q) >= MAX_FAILURES:
        retry = int(LOCKOUT_WINDOW_S - (now - q[0])) + 1
        raise HTTPException(429, "Too many failed sign-in attempts. Try again in a few minutes.", headers={"Retry-After": str(retry)})
    if not q:
        _failures.pop(key, None)


def _record_failure(key: str) -> None:
    if len(_failures) > 10000:  # bounded memory: drop the oldest entries
        for k in list(_failures)[:1000]:
            _failures.pop(k, None)
    _failures.setdefault(key, deque()).append(_now())


@router.post("/auth/login", response_model=AuthOut)
def login(body: Credentials, request: Request, db: Session = Depends(get_db)) -> AuthOut:
    key = _lockout_key(body.username, request)
    _check_not_locked(key)
    user = db.scalar(select(User).where(User.username == body.username))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        _record_failure(key)
        raise HTTPException(401, "Incorrect username or password")  # same message and work for both cases
    _failures.pop(key, None)
    return AuthOut(token=_issue_token(db, user), user=UserOut.model_validate(user))


@router.post("/auth/logout", status_code=204)
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Response:
    _, _, token = (authorization or "").partition(" ")
    if token:
        db.execute(delete(AuthToken).where(AuthToken.token_digest == token_digest(token)))
        db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    if body.age_range is not None:
        user.age_range = body.age_range or None
    if body.goals is not None:
        user.goals = body.goals or None
    if body.preferences is not None:
        unknown = set(body.preferences) - set(ALLOWED_PREFERENCES)
        if unknown:
            raise HTTPException(422, f"Unknown preferences: {sorted(unknown)}")
        user.preferences = {**(user.preferences or {}), **body.preferences}
    db.commit()
    return user


@router.delete("/me", status_code=204)
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    """Data deletion: removes the account and everything stored about it (sessions, repetitions, decisions, tokens)."""
    db.execute(delete(AdaptiveDecision).where(AdaptiveDecision.user_id == user.id))
    for s in db.scalars(select(ExerciseSession).where(ExerciseSession.user_id == user.id)).all():
        db.delete(s)  # cascades to repetitions
    db.execute(delete(AuthToken).where(AuthToken.user_id == user.id))
    db.delete(user)
    db.commit()
    return Response(status_code=204)
