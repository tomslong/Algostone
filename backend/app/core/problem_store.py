"""题目数据存储层 - 与 jsonl 结构对齐."""
import json
import logging
from typing import List, Optional, Dict, Any
from psycopg2.extras import RealDictCursor

from app.core.database import db

logger = logging.getLogger(__name__)


def count_problems() -> int:
    """获取题目总数."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM problems")
        result = cur.fetchone()
        return result[0] if result else 0


def fetch_problems(
    limit: int = 100,
    skip: int = 0,
    difficulty: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取题目列表.

    Args:
        limit: 返回数量限制
        skip: 跳过数量
        difficulty: 难度过滤

    Returns:
        题目字典列表
    """
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM problems"
        params = []

        conditions = []
        if difficulty:
            conditions.append("difficulty = %s")
            params.append(difficulty)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY question_id ASC LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cur.execute(query, params)
        results = cur.fetchall()

        # 转换为普通字典列表
        return [dict(row) for row in results]


def fetch_problem_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    根据 task_id 获取题目详情.

    Args:
        task_id: 题目 ID (如 "two-sum")

    Returns:
        题目字典或 None
    """
    with db.get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM problems WHERE task_id = %s", (task_id,))
        result = cur.fetchone()
        return dict(result) if result else None


def get_test_cases(task_id: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    获取题目的测试用例.

    Args:
        task_id: 题目 ID
        limit: 返回数量限制

    Returns:
        测试用例列表 [{"input": "...", "output": "..."}]
    """
    problem = fetch_problem_by_id(task_id)
    if not problem:
        return []

    input_output = problem.get("input_output", [])
    if isinstance(input_output, str):
        input_output = json.loads(input_output)

    return input_output[:limit]


def get_starter_code(task_id: str) -> Optional[str]:
    """获取题目的 starter_code."""
    problem = fetch_problem_by_id(task_id)
    return problem.get("starter_code") if problem else None


def get_completion(task_id: str) -> Optional[str]:
    """获取题目的 completion (完整答案)."""
    problem = fetch_problem_by_id(task_id)
    return problem.get("completion") if problem else None
