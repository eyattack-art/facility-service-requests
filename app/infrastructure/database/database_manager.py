from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class DatabaseManager:
    def __init__(
        self,
        url: str,
        pool_size: int,
        max_overflow: int,
        pool_pre_ping: bool,
        pool_recycle: int,
        pool_timeout: int,
    ):
        self._engine = create_async_engine(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
            pool_timeout=pool_timeout,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def dispose(self) -> None:
        await self._engine.dispose()

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory
