"""数据库表初始化模块.

在应用启动时自动创建/更新表结构。
"""
import logging
from app.core.database import db

logger = logging.getLogger(__name__)


def ensure_tables_exist():
    """确保所有必要的表存在，不存在则创建."""
    with db.get_connection() as conn:
        cur = conn.cursor()

        # 用户进度表
        _ensure_user_progress_table(cur)

        # 用户代码表 (包含 is_ac 字段)
        _ensure_user_code_table(cur)

        # 聊天会话表
        _ensure_chat_sessions_table(cur)

        conn.commit()


def _ensure_user_progress_table(cur):
    """确保 user_progress 表存在."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_progress (
            device_id VARCHAR(100) PRIMARY KEY,
            current_problem_id VARCHAR(100),
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.debug("user_progress table ensured")


def _ensure_user_code_table(cur):
    """确保 user_code 表存在且包含 is_ac 字段."""
    # 先创建表（如果不存在）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_code (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(100) NOT NULL,
            problem_id VARCHAR(100) NOT NULL,
            code TEXT,
            language VARCHAR(20) DEFAULT 'python',
            is_ac BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_id, problem_id)
        )
    """)

    # 检查 is_ac 字段是否存在，如果不存在则添加
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'user_code' AND column_name = 'is_ac'
    """)

    if not cur.fetchone():
        logger.info("Adding is_ac field to user_code table")
        cur.execute("ALTER TABLE user_code ADD COLUMN is_ac BOOLEAN DEFAULT FALSE")

    # 创建索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_code_device ON user_code(device_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_code_problem ON user_code(problem_id)")

    logger.debug("user_code table ensured")


def _ensure_chat_sessions_table(cur):
    """确保 chat_sessions 表存在."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id VARCHAR(100) PRIMARY KEY,
            user_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            history JSON DEFAULT '[]'::jsonb,
            last_message TEXT,
            problem_id VARCHAR(100)
        )
    """)

    # 创建索引
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_problem ON chat_sessions(problem_id)")

    logger.debug("chat_sessions table ensured")
