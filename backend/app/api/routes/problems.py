"""题目相关路由 - 与 jsonl 结构对齐."""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from app.models.schemas import LeetCodeProblem
from app.core.problem_store import (
    fetch_problems,
    fetch_problem_by_id,
    get_test_cases,
    get_starter_code,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/problems")
async def get_problems_list(
    difficulty: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """
    获取题目列表.

    Args:
        difficulty: 难度过滤 (Easy, Medium, Hard)
        limit: 返回数量限制
        skip: 跳过数量
    """
    problems = fetch_problems(limit=limit, skip=skip, difficulty=difficulty)
    return {
        "total": len(problems),
        "problems": problems
    }


@router.get("/problems/{task_id}")
async def get_problem_detail(task_id: str):
    """
    获取题目详情.

    Args:
        task_id: 题目 ID (如 "two-sum")
    """
    problem = fetch_problem_by_id(task_id)

    if not problem:
        raise HTTPException(status_code=404, detail="题目不存在")

    return problem


@router.get("/problems/{task_id}/starter-code")
async def get_starter_code_endpoint(task_id: str):
    """获取题目代码模板."""
    code = get_starter_code(task_id)

    if not code:
        raise HTTPException(status_code=404, detail="题目不存在")

    return {"task_id": task_id, "starter_code": code}


@router.get("/problems/{task_id}/test-cases")
async def get_test_cases_endpoint(task_id: str, limit: int = 10):
    """
    获取题目测试用例.

    Args:
        task_id: 题目 ID
        limit: 返回数量限制
    """
    test_cases = get_test_cases(task_id, limit=limit)

    if not test_cases:
        raise HTTPException(status_code=404, detail="题目不存在或没有测试用例")

    return {
        "task_id": task_id,
        "test_cases": test_cases
    }
