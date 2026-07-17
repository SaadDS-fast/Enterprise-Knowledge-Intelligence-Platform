from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def database_health() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
