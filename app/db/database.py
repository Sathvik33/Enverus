from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

engine = None
async_session_factory = None


class Base(DeclarativeBase):
    pass


def normalize_db_url(url: str):
    if not url:
        return url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    parsed = make_url(url)
    query = dict(parsed.query)
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    allowed = {"ssl", "timeout", "command_timeout", "statement_cache_size", "server_settings"}
    query = {k: v for k, v in query.items() if k in allowed}
    return parsed.set(query=query)


def get_engine():
    global engine
    if engine is None:
        settings = get_settings()
        db_url = normalize_db_url(settings.DATABASE_URL)
        engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    return engine


def get_session_factory():
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return async_session_factory


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    from app.db.models import Document, TextChunk, TableChunk, ImageChunk, User, ChatHistory  # noqa: F401
    eng = get_engine()
    try:
        async with eng.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    except Exception:
        pass
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
