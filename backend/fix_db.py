import asyncio
from sqlalchemy import text
from app.core.database import get_engine, Base


async def fix():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS analyses CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS repositories CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS analysis_status CASCADE"))
        print("Tables dropped")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created")


if __name__ == "__main__":
    asyncio.run(fix())
