from __future__ import annotations

from typing import Generic, TypeVar, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self._session = session
        self._model = model

    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_id(self, id: int) -> T | None:
        return await self._session.get(self._model, id)

    async def list(self, offset: int = 0, limit: int = 100) -> list[T]:
        statement = select(self._model).offset(offset).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def save(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()
