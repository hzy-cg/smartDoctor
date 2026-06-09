"""数据库迁移：为 knowledge_uploads 表添加 received_chunk_map 字段"""
import asyncio
from app.infrastructure.persistence.database import engine
from sqlalchemy import text


async def migrate():
    async with engine.connect() as conn:
        # 检查列是否已存在（PG 9.2 不支持 IF NOT EXISTS）
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'knowledge_uploads' AND column_name = 'received_chunk_map'"
        ))
        exists = result.fetchone() is not None

        if exists:
            print("Column 'received_chunk_map' already exists, skipping.")
            return

        await conn.execute(text(
            "ALTER TABLE knowledge_uploads ADD COLUMN received_chunk_map VARCHAR(2048)"
        ))
        await conn.commit()
        print("Migration OK: added column 'received_chunk_map' to 'knowledge_uploads'")


if __name__ == "__main__":
    asyncio.run(migrate())