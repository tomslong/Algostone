"""FastAPI 主应用入口 - 安全增强版.

安全特性:
- 速率限制
- 安全响应头
- CORS 配置
- TrustedHost 验证
- 请求 ID 追踪
- 结构化日志
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import uuid
import time

from app.api.routes import (
    chat, health, execute, settings as settings_router,
    problems, auth, user
)
from app.core.config import settings, validate_settings_on_startup
from app.core.database import db

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 速率限制器
# ============================================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_CHAT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
    headers_enabled=True  # 在响应头添加速率限制信息
)


# ============================================================================
# 应用生命周期
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    logger.info(f"AlgoStone 后端启动中...")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"API前缀: {settings.API_V1_PREFIX}")

    # 配置验证
    try:
        validate_settings_on_startup()
        logger.info("配置验证通过")
    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        if settings.is_production:
            raise

    # 初始化数据库连接池
    try:
        db.initialize()
        logger.info("数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        if not settings.is_development:
            raise

    # 自动创建/更新表结构
    try:
        from app.core.init_tables import ensure_tables_exist
        ensure_tables_exist()
        logger.info("数据库表结构检查完成")
    except Exception as e:
        logger.warning(f"数据库表初始化警告: {e}")

    # 记录启动状态
    startup_time = time.time()
    logger.info(f"AlgoStone 后端启动完成 (耗时: {time.time() - startup_time:.3f}秒)")

    yield

    # 关闭时清理
    logger.info("AlgoStone 后端关闭中...")
    db.close()
    logger.info("AlgoStone 后端已关闭")


# ============================================================================
# 应用初始化
# ============================================================================

app = FastAPI(
    title="AlgoStone API",
    description="算法AI智能体后端服务 - 安全增强版",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG or settings.is_development else None,  # 生产环境隐藏文档
    redoc_url="/redoc" if settings.DEBUG or settings.is_development else None,
)

# 挂载速率限制器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================================
# 中间件
# ============================================================================

# 1. TrustedHost (防止 Host Header 攻击)
if not settings.is_development:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.SECURITY_ALLOWED_HOSTS + ["*"]  # 开发环境允许所有主机
    )

# 2. CORS (跨域资源共享)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # 明确指定允许的方法
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Client-Version"
    ],  # 明确指定的请求头
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,  # 预检请求缓存时间
)


# 3. 自定义安全头中间件
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全响应头."""
    response = await call_next(request)

    # 安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # 内容安全策略 (CSP)
    if settings.is_production:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

    # 移除服务器信息
    response.headers["Server"] = "AlgoStone"

    return response


# 4. 请求 ID 中间件
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """添加请求 ID 用于追踪."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# 5. 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求信息."""
    start_time = time.time()

    # 记录请求
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"(client: {request.client.host if request.client else 'unknown'})"
    )

    response = await call_next(request)

    # 记录响应
    process_time = time.time() - start_time
    status_code = response.status_code

    log_level = logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(
        log_level,
        f"Response: {request.method} {request.url.path} "
        f"status={status_code} "
        f"time={process_time:.3f}s"
    )

    # 添加处理时间头
    response.headers["X-Process-Time"] = f"{process_time:.3f}"

    return response


# ============================================================================
# 异常处理
# ============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP 异常处理."""
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "request_id": request_id,
            "status": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理."""
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "请求参数验证失败",
            "details": exc.errors(),
            "request_id": request_id,
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"request_id": request_id}
    )

    # 生产环境不暴露详细错误信息
    if settings.is_production:
        message = "服务器内部错误"
    else:
        message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": message,
            "request_id": request_id,
        }
    )


# ============================================================================
# 路由注册
# ============================================================================

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(user.router, prefix=settings.API_V1_PREFIX + "/user", tags=["User"])
app.include_router(chat.router, prefix=settings.API_V1_PREFIX + "/chat", tags=["Chat"])
app.include_router(execute.router, prefix=settings.API_V1_PREFIX, tags=["Execute"])
app.include_router(settings_router.router, prefix=settings.API_V1_PREFIX, tags=["Settings"])
app.include_router(problems.router, prefix=settings.API_V1_PREFIX, tags=["Problems"])
# 兼容旧路径（不带 v1）
app.include_router(problems.router, prefix="/api", tags=["Problems-Legacy"])
app.include_router(execute.router, prefix="/api", tags=["Execute-Legacy"])


# ============================================================================
# 根路径
# ============================================================================

@app.get("/")
async def root():
    """根路径."""
    return {
        "message": "Welcome to AlgoStone API",
        "version": "0.2.0",
        "docs": "/docs" if settings.DEBUG or settings.is_development else None,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """健康检查端点."""
    db_health = db.health_check()

    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": "0.2.0",
        "environment": settings.ENVIRONMENT,
        "database": db_health,
    }
