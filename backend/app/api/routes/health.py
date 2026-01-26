"""健康检查路由 - Production-Ready Edition.

提供全面的系统健康监控:
- 基础健康检查
- 详细状态检查
- LLM可用性检查
- 数据库连接检查
- Redis连接检查
"""
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from langgraph_agent.llm import get_llm

router = APIRouter()


# ============================================================================
# 响应模型
# ============================================================================

class HealthResponse(BaseModel):
    """健康检查响应."""
    status: str
    service: str
    version: str = "1.0.0"
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """详细健康检查响应."""
    status: str
    service: str
    version: str = "1.0.0"
    timestamp: str
    uptime_seconds: float
    checks: Dict[str, Any]


class ComponentStatus(BaseModel):
    """组件状态."""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    response_time_ms: Optional[float] = None


# ============================================================================
# 服务启动时间
# ============================================================================

START_TIME = time.time()


# ============================================================================
# 基础健康检查
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    基础健康检查端点.

    用于负载均衡器和容器编排系统的健康检查。

    Returns:
        HealthResponse: 服务健康状态
    """
    return HealthResponse(
        status="healthy",
        service="AlgoStone API",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """
    简单ping测试.

    Returns:
        {"message": "pong"}
    """
    return {"message": "pong"}


# ============================================================================
# 详细健康检查
# ============================================================================

@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    详细健康检查端点.

    检查所有系统组件的状态:
    - LLM服务
    - 数据库
    - Redis
    - 磁盘空间

    Returns:
        DetailedHealthResponse: 详细的健康状态
    """
    uptime = time.time() - START_TIME
    checks = {}

    # 并发执行所有检查
    check_results = await asyncio.gather(
        check_llm(),
        check_database(),
        check_redis(),
        check_disk_space(),
        return_exceptions=True
    )

    checks["llm"] = _handle_check_result(check_results[0], "LLM")
    checks["database"] = _handle_check_result(check_results[1], "Database")
    checks["redis"] = _handle_check_result(check_results[2], "Redis")
    checks["disk"] = _handle_check_result(check_results[3], "Disk")

    # 确定整体状态
    overall_status = "healthy"
    for check in checks.values():
        if check.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break
        elif check.get("status") == "degraded":
            overall_status = "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        service="AlgoStone API",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        checks=checks
    )


# ============================================================================
# LLM健康检查
# ============================================================================

@router.get("/health/llm")
async def check_llm_endpoint():
    """
    检查LLM服务可用性.

    Returns:
        LLM服务状态
    """
    return await check_llm()


async def check_llm() -> Dict[str, Any]:
    """检查LLM服务."""
    start_time = time.time()

    try:
        # 尝试获取LLM实例
        llm = get_llm(streaming=False)

        # 发送一个简单的测试请求
        from langchain_core.messages import HumanMessage
        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="ping")]),
            timeout=10.0
        )

        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "message": "LLM服务正常",
            "response_time_ms": round(response_time, 2),
            "model": getattr(settings, "MODEL_NAME", "unknown")
        }

    except asyncio.TimeoutError:
        return {
            "status": "degraded",
            "message": "LLM服务响应超时",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"LLM服务不可用: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


# ============================================================================
# 数据库健康检查
# ============================================================================

async def check_database() -> Dict[str, Any]:
    """检查数据库连接."""
    start_time = time.time()

    try:
        from app.core.database import get_db

        # 尝试获取数据库连接
        db = get_db()

        # 执行简单查询
        await db.execute("SELECT 1")

        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "message": "数据库连接正常",
            "response_time_ms": round(response_time, 2)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"数据库连接失败: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


# ============================================================================
# Redis健康检查
# ============================================================================

async def check_redis() -> Dict[str, Any]:
    """检查Redis连接."""
    start_time = time.time()

    try:
        import redis.asyncio as redis

        # 创建Redis连接
        redis_client = redis.from_url(
            settings.REDIS_URL,
            socket_timeout=2,
            socket_connect_timeout=2
        )

        # 执行PING
        await redis_client.ping()
        await redis_client.close()

        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "message": "Redis连接正常",
            "response_time_ms": round(response_time, 2)
        }

    except Exception as e:
        return {
            "status": "degraded",
            "message": f"Redis连接失败: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


# ============================================================================
# 磁盘空间检查
# ============================================================================

async def check_disk_space() -> Dict[str, Any]:
    """检查磁盘空间."""
    try:
        import shutil

        # 获取磁盘使用情况
        usage = shutil.disk_usage(".")

        # 计算使用百分比
        usage_percent = (usage.used / usage.total) * 100

        # 确定状态
        if usage_percent > 90:
            status = "unhealthy"
            message = f"磁盘空间不足 ({usage_percent:.1f}%)"
        elif usage_percent > 75:
            status = "degraded"
            message = f"磁盘空间紧张 ({usage_percent:.1f}%)"
        else:
            status = "healthy"
            message = f"磁盘空间充足 ({usage_percent:.1f}%)"

        return {
            "status": status,
            "message": message,
            "usage_percent": round(usage_percent, 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "total_gb": round(usage.total / (1024**3), 2)
        }

    except Exception as e:
        return {
            "status": "degraded",
            "message": f"无法检查磁盘空间: {str(e)}"
        }


# ============================================================================
# 辅助函数
# ============================================================================

def _handle_check_result(result: Any, component_name: str) -> Dict[str, Any]:
    """处理检查结果."""
    if isinstance(result, Exception):
        return {
            "status": "unhealthy",
            "message": f"{component_name}检查出错: {str(result)}"
        }
    return result


# ============================================================================
# Prometheus指标端点
# ============================================================================

@router.get("/metrics")
async def metrics():
    """
    Prometheus格式的指标端点.

    Returns:
        Prometheus格式的指标
    """
    uptime = time.time() - START_TIME

    metrics_text = f"""# HELP algostone_uptime_seconds 服务运行时间(秒)
# TYPE algostone_uptime_seconds gauge
algostone_uptime_seconds {uptime:.2f}

# HELP algostone_health_status 服务健康状态 (1=healthy, 0=unhealthy)
# TYPE algostone_health_status gauge
algostone_health_status 1
"""
    return metrics_text
