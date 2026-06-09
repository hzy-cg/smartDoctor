"""数据库迁移：为 knowledge_docs 表添加 v2.1 解析元数据字段"""
import asyncio
from app.infrastructure.persistence.database import engine
from sqlalchemy import text


async def migrate():
    columns = {
        "file_size": "BIGINT DEFAULT 0 NOT NULL",
        "encoding": "VARCHAR(32)",
        "parse_method": "VARCHAR(32)",
        "page_count": "INTEGER",
        "parse_duration_ms": "FLOAT",
    }

    async with engine.connect() as conn:
        for col_name, col_type in columns.items():
            # 检查列是否已存在
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'knowledge_docs' AND column_name = :col"
            ), {"col": col_name})
            exists = result.fetchone() is not None

            if exists:
                print(f"  SKIP: column '{col_name}' already exists")
                continue

            await conn.execute(text(
                f"ALTER TABLE knowledge_docs ADD COLUMN {col_name} {col_type}"
            ))
            print(f"  OK: added column '{col_name}' ({col_type})")

        await conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
