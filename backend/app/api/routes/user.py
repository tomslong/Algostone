"""用户进度和代码管理 API (匿名用户系统)."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import db

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class SaveProgressRequest(BaseModel):
    """保存进度请求."""
    device_id: str = Field(..., description="设备ID")
    current_problem_id: Optional[str] = Field(None, description="当前题目ID")


class GetProgressResponse(BaseModel):
    """获取进度响应."""
    device_id: str
    current_problem_id: Optional[str] = None
    last_active_at: Optional[str] = None


class SaveCodeRequest(BaseModel):
    """保存代码请求."""
    device_id: str = Field(..., description="设备ID")
    problem_id: str = Field(..., description="题目ID")
    code: str = Field(..., description="代码内容")
    language: str = Field(default="python", description="编程语言")


class GetCodeResponse(BaseModel):
    """获取代码响应."""
    problem_id: str
    code: str
    language: str
    updated_at: Optional[str] = None


# ============================================================================
# API 端点
# ============================================================================

@router.post("/progress", response_model=dict)
async def save_progress(request: SaveProgressRequest):
    """
    保存用户当前进度.

    记录用户正在做的题目，下次打开时可以恢复。
    """
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            # 使用 UPSERT (PostgreSQL 9.5+)
            cur.execute("""
                INSERT INTO user_progress (device_id, current_problem_id, last_active_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id)
                DO UPDATE SET
                    current_problem_id = EXCLUDED.current_problem_id,
                    last_active_at = EXCLUDED.last_active_at
                RETURNING current_problem_id, last_active_at
            """, (request.device_id, request.current_problem_id))

            row = cur.fetchone()
            conn.commit()

            logger.info(f"Progress saved: device_id={request.device_id}, problem={request.current_problem_id}")

            return {
                "status": "success",
                "current_problem_id": row[0],
                "last_active_at": row[1].isoformat() if row[1] else None
            }

    except Exception as e:
        logger.error(f"Failed to save progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{device_id}", response_model=GetProgressResponse)
async def get_progress(device_id: str):
    """获取用户当前进度."""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT device_id, current_problem_id, last_active_at
                FROM user_progress
                WHERE device_id = %s
            """, (device_id,))

            row = cur.fetchone()

            if not row:
                return GetProgressResponse(
                    device_id=device_id,
                    current_problem_id=None,
                    last_active_at=None
                )

            return GetProgressResponse(
                device_id=row[0],
                current_problem_id=row[1],
                last_active_at=row[2].isoformat() if row[2] else None
            )

    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code", response_model=dict)
async def save_code(request: SaveCodeRequest):
    """
    保存用户代码.

    每个用户对每个题目只保存一份最新的代码。
    """
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            # 使用 UPSERT
            cur.execute("""
                INSERT INTO user_code (device_id, problem_id, code, language, created_at, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id, problem_id)
                DO UPDATE SET
                    code = EXCLUDED.code,
                    language = EXCLUDED.language,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, updated_at
            """, (request.device_id, request.problem_id, request.code, request.language))

            row = cur.fetchone()
            conn.commit()

            logger.info(f"Code saved: device_id={request.device_id}, problem={request.problem_id}")

            return {
                "status": "success",
                "id": row[0],
                "updated_at": row[1].isoformat() if row[1] else None
            }

    except Exception as e:
        logger.error(f"Failed to save code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/{device_id}/{problem_id}", response_model=GetCodeResponse)
async def get_code(device_id: str, problem_id: str):
    """获取用户指定题目的代码."""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT problem_id, code, language, updated_at
                FROM user_code
                WHERE device_id = %s AND problem_id = %s
            """, (device_id, problem_id))

            row = cur.fetchone()

            if not row:
                return GetCodeResponse(
                    problem_id=problem_id,
                    code="",
                    language="python",
                    updated_at=None
                )

            return GetCodeResponse(
                problem_id=row[0],
                code=row[1] or "",
                language=row[2],
                updated_at=row[3].isoformat() if row[3] else None
            )

    except Exception as e:
        logger.error(f"Failed to get code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/{device_id}", response_model=list[GetCodeResponse])
async def get_all_code(device_id: str):
    """获取用户所有保存的代码."""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT problem_id, code, language, updated_at
                FROM user_code
                WHERE device_id = %s
                ORDER BY updated_at DESC
            """, (device_id,))

            rows = cur.fetchall()

            return [
                GetCodeResponse(
                    problem_id=row[0],
                    code=row[1] or "",
                    language=row[2],
                    updated_at=row[3].isoformat() if row[3] else None
                )
                for row in rows
            ]

    except Exception as e:
        logger.error(f"Failed to get all code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 提交相关
# ============================================================================

class SubmitRequest(BaseModel):
    """提交代码请求."""
    device_id: str = Field(..., description="设备ID")
    problem_id: str = Field(..., description="题目ID")
    code: str = Field(..., description="代码内容")
    language: str = Field(default="python", description="编程语言")
    test_results: list = Field(..., description="测试结果")


class SubmitResponse(BaseModel):
    """提交响应."""
    status: str
    is_ac: bool
    passed: int
    total: int
    message: str


@router.post("/submit", response_model=SubmitResponse)
async def submit_code(request: SubmitRequest):
    """
    提交代码.

    运行所有测试用例，如果全部通过则标记为 AC (Accepted).
    """
    try:
        # 统计测试结果
        total = len(request.test_results)
        passed = sum(1 for r in request.test_results if r.get("passed", False))
        is_ac = (passed == total and total > 0)

        # 保存代码和 AC 状态
        with db.get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user_code (device_id, problem_id, code, language, is_ac, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id, problem_id)
                DO UPDATE SET
                    code = EXCLUDED.code,
                    language = EXCLUDED.language,
                    is_ac = EXCLUDED.is_ac,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """, (request.device_id, request.problem_id, request.code, request.language, is_ac))

            conn.commit()

        if is_ac:
            logger.info(f"AC! device_id={request.device_id}, problem={request.problem_id}")
        else:
            logger.info(f"Submit failed: device_id={request.device_id}, problem={request.problem_id}, passed={passed}/{total}")

        return SubmitResponse(
            status="success",
            is_ac=is_ac,
            passed=passed,
            total=total,
            message="All tests passed! 🎉" if is_ac else f"{passed}/{total} tests passed"
        )

    except Exception as e:
        logger.error(f"Failed to submit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ac-problems/{device_id}")
async def get_ac_problems(device_id: str):
    """获取用户已通过的题目列表."""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT problem_id
                FROM user_code
                WHERE device_id = %s AND is_ac = TRUE
                ORDER BY updated_at DESC
            """, (device_id,))

            rows = cur.fetchall()

            return {
                "ac_problems": [row[0] for row in rows]
            }

    except Exception as e:
        logger.error(f"Failed to get AC problems: {e}")
        raise HTTPException(status_code=500, detail=str(e))
