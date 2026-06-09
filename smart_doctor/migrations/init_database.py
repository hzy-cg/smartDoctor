"""
SmartDoctor 数据库自动初始化脚本

用法:
    python -m migrations.init_database

功能:
    1. 检测数据库连接
    2. 基于所有 ORM 模型创建表（CREATE TABLE IF NOT EXISTS）
    3. 创建索引和约束
    4. 输出初始化结果

依赖: 需要安装项目依赖（pip install -e .）
"""
import asyncio
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def init_database():
    """基于 ORM 模型初始化所有数据表"""
    from sqlalchemy import text
    from app.infrastructure.persistence.database import engine, Base
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.doctor import (
        DoctorRole, DigitalHuman, DoctorKnowledge, Favorite, Department,
    )
    from app.infrastructure.persistence.models.conversation import Conversation, Message
    from app.infrastructure.persistence.models.knowledge import KnowledgeDoc
    from app.infrastructure.persistence.models.upload_session import UploadSession
    from app.infrastructure.persistence.models.audit_log import AuditLog
    from app.infrastructure.persistence.models.outbox import OutboxEvent

    print("=" * 60)
    print("SmartDoctor v2.2 — 数据库初始化")
    print("=" * 60)

    # 测试连接
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"\n[OK] 数据库连接成功")
            print(f"     {version}")
    except Exception as e:
        print(f"\n[ERROR] 数据库连接失败: {e}")
        print("\n请检查:")
        print("  1. PostgreSQL 服务是否启动")
        print("  2. .env 文件中的 DATABASE_URL 配置是否正确")
        print("  3. 数据库 'smart_doctor' 是否已创建")
        return False

    # 创建所有表
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("\n[OK] 所有数据表创建/验证完成")

        # 列出所有已创建的表
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
            ))
            tables = [row[0] for row in result.fetchall()]
            print(f"\n     已创建 {len(tables)} 张表:")
            for t in tables:
                print(f"       - {t}")

        # 检查 uuid-ossp 扩展
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'uuid-ossp'"
            ))
            has_ext = result.scalar() > 0
            if not has_ext:
                print("\n[WARN] uuid-ossp 扩展未安装，UUID 默认值可能不可用")
                print("      安装命令: CREATE EXTENSION \"uuid-ossp\";")
            else:
                print("\n[OK] uuid-ossp 扩展已就绪")

    except Exception as e:
        print(f"\n[ERROR] 建表失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("数据库初始化完成!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
