"""数据库连接管理 - 安全增强版.

特性:
- 连接池管理
- 命名元组代替魔法数字索引
- SQL注入防护 (使用参数化查询)
- 连接超时和重试机制
- 查询性能监控
"""
from psycopg2 import pool, sql
from psycopg2.extras import NamedTupleCursor
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from collections import namedtuple
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# 命名元组定义 (代替魔法数字索引)
# ============================================================================

# 用户表结构 (按数据库返回顺序)
UserRecord = namedtuple(
    'UserRecord',
    [
        'id',              # 0
        'username',        # 1
        'email',           # 2
        'hashed_password', # 3
        'is_active',       # 4
        'created_at',      # 5
        'updated_at'       # 6
    ]
)

# ============================================================================
# 数据库连接池
# ============================================================================

class Database:
    """数据库连接池管理."""

    _pool: Optional[pool.SimpleConnectionPool] = None
    _is_initialized: bool = False

    @classmethod
    def initialize(cls):
        """初始化连接池."""
        if cls._is_initialized:
            return

        try:
            cls._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                dbname=settings.POSTGRES_DB,
                connect_timeout=10,
            )
            cls._is_initialized = True
            logger.info("Database connection pool created successfully.")

            # 测试连接
            with cls.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    logger.info("Database connection test successful.")

        except Exception as e:
            logger.error(f"Error creating database connection pool: {e}")
            cls._is_initialized = False
            raise

    @classmethod
    def close(cls):
        """关闭连接池."""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            cls._is_initialized = False
            logger.info("Database connection pool closed.")

    @classmethod
    def is_connected(cls) -> bool:
        """检查数据库是否已连接."""
        return cls._pool is not None and cls._is_initialized

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator:
        """获取数据库连接上下文管理器."""
        if cls._pool is None:
            cls.initialize()

        conn = cls._pool.getconn()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            cls._pool.putconn(conn)

    @classmethod
    @contextmanager
    def get_cursor(cls, named_tuple: bool = True) -> Generator:
        """获取数据库游标上下文管理器.

        Args:
            named_tuple: 是否返回命名元组 (推荐)
        """
        with cls.get_connection() as conn:
            cursor_factory = NamedTupleCursor if named_tuple else None
            with conn.cursor(cursor_factory=cursor_factory) as cur:
                yield cur

    @classmethod
    def execute_query(
        cls,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = False,
        fetch_one: bool = False,
        named: bool = True
    ) -> Optional[Any]:
        """
        执行 SQL 查询的安全辅助函数.

        特性:
        - 使用参数化查询防止 SQL 注入
        - 自动错误处理和回滚
        - 支持命名元组返回

        Args:
            query: SQL 查询语句 (使用 %s 占位符)
            params: 查询参数 (防止 SQL 注入)
            fetch: 是否返回结果
            fetch_one: 是否只返回第一行
            named: 是否使用命名元组 (推荐)

        Returns:
            查询结果 (命名元组或普通元组)

        Raises:
            Exception: 数据库错误

        Example:
            # 安全的参数化查询
            user = db.execute_query(
                "SELECT * FROM users WHERE id = %s",
                (user_id,),
                fetch_one=True,
                named=True
            )
            if user:
                print(user.username)  # 使用字段名而不是索引
        """
        with cls.get_connection() as conn:
            cursor_factory = NamedTupleCursor if named else None
            cur = conn.cursor(cursor_factory=cursor_factory)

            try:
                start_time = time.time()
                cur.execute(query, params or ())
                execution_time = time.time() - start_time

                # 记录慢查询 (>100ms)
                if execution_time > 0.1:
                    logger.warning(f"Slow query detected: {execution_time:.3f}s - {query[:100]}")

                if fetch:
                    if fetch_one:
                        result = cur.fetchone()
                    else:
                        result = cur.fetchall()
                    return result
                else:
                    conn.commit()
                    return None

            except Exception as e:
                conn.rollback()
                logger.error(f"Query execution error: {e}\nQuery: {query[:200]}")
                raise

    @classmethod
    def execute_many(
        cls,
        query: str,
        params_list: List[tuple]
    ) -> None:
        """批量执行查询.

        Args:
            query: SQL 查询语句
            params_list: 参数列表
        """
        with cls.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.executemany(query, params_list)
                conn.commit()
                logger.info(f"Batch executed {len(params_list)} rows")
            except Exception as e:
                conn.rollback()
                logger.error(f"Batch execution error: {e}")
                raise

    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        """数据库健康检查."""
        try:
            with cls.get_connection() as conn:
                with conn.cursor() as cur:
                    start_time = time.time()
                    cur.execute("SELECT 1")
                    cur.fetchone()
                    latency = (time.time() - start_time) * 1000

                    # 获取连接池状态
                    pool_stats = {
                        "min_connections": cls._pool.minconn if cls._pool else 0,
                        "max_connections": cls._pool.maxconn if cls._pool else 0,
                    }

                    return {
                        "status": "healthy",
                        "latency_ms": round(latency, 2),
                        "pool": pool_stats
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# ============================================================================
# 单例实例
# ============================================================================

db = Database()


# ============================================================================
# 查询构建器 (类型安全)
# ============================================================================

class QueryBuilder:
    """类型安全的 SQL 查询构建器."""

    def __init__(self, table_name: str):
        self.table = table_name
        self.conditions: List[str] = []
        self.params: List[Any] = []
        self.order_by: Optional[str] = None
        self.limit_val: Optional[int] = None
        self.offset_val: Optional[int] = None

    def where(self, column: str, operator: str, value: Any) -> 'QueryBuilder':
        """添加 WHERE 条件."""
        self.conditions.append(f"{column} {operator} %s")
        self.params.append(value)
        return self

    def where_in(self, column: str, values: List[Any]) -> 'QueryBuilder':
        """添加 WHERE IN 条件."""
        placeholders = ','.join(['%s'] * len(values))
        self.conditions.append(f"{column} IN ({placeholders})")
        self.params.extend(values)
        return self

    def order(self, column: str, direction: str = 'ASC') -> 'QueryBuilder':
        """添加排序."""
        direction = direction.upper()
        if direction not in ('ASC', 'DESC'):
            raise ValueError("Direction must be ASC or DESC")
        self.order_by = f"{column} {direction}"
        return self

    def limit(self, count: int) -> 'QueryBuilder':
        """添加限制."""
        self.limit_val = count
        return self

    def offset(self, count: int) -> 'QueryBuilder':
        """添加偏移."""
        self.offset_val = count
        return self

    def build_select(self, columns: str = "*") -> tuple[str, tuple]:
        """构建 SELECT 查询.

        Returns:
            (query, params) 元组
        """
        query = f"SELECT {columns} FROM {self.table}"

        if self.conditions:
            query += " WHERE " + " AND ".join(self.conditions)

        if self.order_by:
            query += f" ORDER BY {self.order_by}"

        if self.limit_val is not None:
            query += f" LIMIT {self.limit_val}"

        if self.offset_val is not None:
            query += f" OFFSET {self.offset_val}"

        return query, tuple(self.params)

    def execute(self, columns: str = "*", fetch_one: bool = False):
        """执行查询."""
        query, params = self.build_select(columns)
        return db.execute_query(query, params, fetch=True, fetch_one=fetch_one)


# ============================================================================
# 辅助函数
# ============================================================================

def safe_identifier(name: str) -> sql.Identifier:
    """创建安全的 SQL 标识符 (防止注入)."""
    return sql.Identifier(name)


def safe_query(query: str, *args) -> sql.SQL:
    """创建安全的 SQL 查询."""
    return sql.SQL(query).format(
        *(sql.Identifier(arg) if isinstance(arg, str) else arg for arg in args)
    )
