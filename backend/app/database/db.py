import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.core.config import settings


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    age_range: Mapped[str | None] = mapped_column(String(16), nullable=True)
    goals: Mapped[str | None] = mapped_column(String(256), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthToken(Base):
    """Bearer sessions. Only a SHA-256 digest of the token is stored."""
    __tablename__ = "auth_tokens"
    token_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExerciseSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # null = guest
    exercise_id: Mapped[str] = mapped_column(String(64))
    is_demo: Mapped[bool] = mapped_column(default=False)  # synthetic demo data: never feeds history or analytics
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    ws_key: Mapped[str | None] = mapped_column(String(64), nullable=True)  # per-session secret for the live stream
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    repetitions: Mapped[list["Repetition"]] = relationship(back_populates="session", cascade="all, delete-orphan",
                                                           order_by="Repetition.index")


class Repetition(Base):
    __tablename__ = "repetitions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    index: Mapped[int] = mapped_column(Integer)
    range_of_motion_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    counted: Mapped[bool] = mapped_column(Boolean, default=False)
    reliable: Mapped[bool] = mapped_column(Boolean, default=True)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    session: Mapped[ExerciseSession] = relationship(back_populates="repetitions")


class AdaptiveDecision(Base):
    """One software recommendation made at the end of a (non-demo) session of a signed-in user."""
    __tablename__ = "adaptive_decisions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    exercise_id: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    from_level: Mapped[int] = mapped_column(Integer)
    to_level: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))
    classification: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# columns added after the first prototype: older local databases are upgraded in place, never dropped
_ADDED_COLUMNS = {"sessions": [("ws_key", "VARCHAR(64)")],
                  "repetitions": [("counted", "BOOLEAN DEFAULT 0"), ("reliable", "BOOLEAN DEFAULT 1")]}


def init_db(eng=None) -> None:
    eng = eng or engine
    Base.metadata.create_all(eng)
    insp = inspect(eng)
    with eng.begin() as conn:
        for table, cols in _ADDED_COLUMNS.items():
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def reset_db() -> None:
    Base.metadata.drop_all(engine)
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
