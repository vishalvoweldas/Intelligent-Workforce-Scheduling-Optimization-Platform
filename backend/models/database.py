"""Database connection and session management with dynamic profile switching."""
import os
from typing import Generator
from sqlalchemy.orm import Session
from backend.models.profile_manager import (
    Base,
    get_active_profile,
    set_active_profile,
    get_session_factory,
    get_engine_for_profile,
    ensure_profile_database,
    PROFILE_STARTER,
    PROFILE_FULL
)

# Ensure default starter database is present and initialized
ensure_profile_database(PROFILE_STARTER)


class DynamicEngineProxy:
    """Proxies engine method calls to the active dataset profile engine."""
    def __getattr__(self, name):
        prof = get_active_profile()
        target = get_engine_for_profile(prof)
        return getattr(target, name)


class DynamicSessionLocal:
    """Callable sessionmaker proxy that binds to the active dataset profile."""
    def __call__(self, *args, **kwargs) -> Session:
        prof = get_active_profile()
        factory = get_session_factory(prof)
        return factory(*args, **kwargs)

    def configure(self, **kwargs):
        prof = get_active_profile()
        factory = get_session_factory(prof)
        return factory.configure(**kwargs)


engine = DynamicEngineProxy()
SessionLocal = DynamicSessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for obtaining a database session bound to the active profile."""
    prof = get_active_profile()
    factory = get_session_factory(prof)
    db = factory()
    try:
        yield db
    finally:
        db.close()
