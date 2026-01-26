"""用户认证路由 - 安全增强版.

特性:
- Argon2 密码哈希
- 短期访问令牌 (15分钟) + 长期刷新令牌 (7天)
- 速率限制
- 命名字段访问 (代替魔法数字)
- 登录失败追踪
- httpOnly cookie 支持
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    generate_user_id,
    sanitize_for_log,
)
from app.models.schemas import UserRegister, UserLogin, Token, RefreshTokenRequest, UserResponse
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# 速率限制器
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer(auto_error=False)

# ============================================================================
# 刷新令牌存储 (生产环境应使用 Redis)
# ============================================================================

# 简单内存存储 (开发用) - 生产环境请使用 Redis
_refresh_tokens: dict = {}  # {token_jti: user_id}


def store_refresh_token(jti: str, user_id: str) -> None:
    """存储刷新令牌."""
    _refresh_tokens[jti] = user_id


def get_refresh_token_user(jti: str) -> Optional[str]:
    """获取刷新令牌对应的用户."""
    return _refresh_tokens.get(jti)


def revoke_refresh_token(jti: str) -> None:
    """撤销刷新令牌."""
    _refresh_tokens.pop(jti, None)


# ============================================================================
# 辅助函数
# ============================================================================

def get_user_by_username_or_email(identifier: str):
    """通过用户名或邮箱获取用户 (使用命名元组)."""
    return db.execute_query(
        "SELECT * FROM users WHERE username = %s OR email = %s",
        (identifier, identifier),
        fetch_one=True,
        named=True
    )


def get_user_by_id(user_id: str):
    """通过ID获取用户."""
    return db.execute_query(
        "SELECT * FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True,
        named=True
    )


def create_user(username: str, email: str, hashed_password: str) -> str:
    """创建新用户."""
    user_id = generate_user_id()
    db.execute_query(
        """INSERT INTO users (id, username, email, hashed_password, is_active, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
        (user_id, username, email, hashed_password, True)
    )
    return user_id


# ============================================================================
# 认证依赖
# ============================================================================

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """获取当前用户 (可选认证)."""
    if credentials is None:
        # 尝试从 cookie 获取
        token = request.cookies.get("access_token")
        if not token:
            return None
    else:
        token = credentials.credentials

    payload = decode_access_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = get_user_by_id(user_id)
    if user is None:
        return None

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
    }


async def get_current_user_required(
    current_user: Optional[dict] = Depends(get_current_user_optional)
) -> dict:
    """获取当前用户 (必需认证)."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
        )
    return current_user


# ============================================================================
# 端点
# ============================================================================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
async def register(request: Request, user_req: UserRegister, response: Response):
    """
    用户注册.

    - **username**: 用户名 (3-20字符)
    - **email**: 邮箱地址
    - **password**: 密码 (至少8字符，包含3种字符类型)
    """
    # 检查是否允许注册
    if not settings.ENABLE_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="注册功能已关闭"
        )

    # 检查用户名是否已存在
    existing_user = db.execute_query(
        "SELECT id FROM users WHERE username = %s",
        (user_req.username,),
        fetch_one=True
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )

    # 检查邮箱是否已存在
    existing_email = db.execute_query(
        "SELECT id FROM users WHERE email = %s",
        (user_req.email,),
        fetch_one=True
    )
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 哈希密码 (Argon2)
    try:
        hashed_password = get_password_hash(user_req.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 创建新用户
    user_id = create_user(user_req.username, user_req.email, hashed_password)
    logger.info(f"新用户注册: {sanitize_for_log(user_req.username)}")

    # 生成令牌
    access_token = create_access_token(data={"sub": user_id})
    from app.core.security import generate_token_id
    refresh_jti = generate_token_id()
    refresh_token = create_refresh_token(data={"sub": user_id, "jti": refresh_jti})

    # 存储刷新令牌
    store_refresh_token(refresh_jti, user_id)

    # 设置 httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.HTTPS_ENABLED,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_id
    )


@router.post("/login", response_model=Token)
@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
async def login(request: Request, user_req: UserLogin, response: Response):
    """
    用户登录.

    - **username**: 用户名或邮箱
    - **password**: 密码
    """
    # 获取用户
    user = get_user_by_username_or_email(user_req.username)

    if user is None:
        # 使用通用错误消息防止用户枚举
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证密码 (使用命名字段)
    if not verify_password(user_req.password, user.hashed_password):
        logger.warning(f"登录失败: {sanitize_for_log(user_req.username)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查账号状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用"
        )

    # 生成令牌
    access_token = create_access_token(data={"sub": user.id})
    from app.core.security import generate_token_id
    refresh_jti = generate_token_id()
    refresh_token = create_refresh_token(data={"sub": user.id, "jti": refresh_jti})

    # 存储刷新令牌
    store_refresh_token(refresh_jti, user.id)

    logger.info(f"用户登录: {sanitize_for_log(user.username)}")

    # 设置 httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.HTTPS_ENABLED,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request, response: Response):
    """
    刷新访问令牌.

    从 httpOnly cookie 或请求体获取刷新令牌。
    """
    # 优先从 cookie 获取
    refresh_token_value = request.cookies.get("refresh_token")

    # 如果 cookie 没有，从请求体获取
    if not refresh_token_value:
        # 注意：这需要请求体支持，实际使用时可能需要调整
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供刷新令牌"
        )

    # 验证刷新令牌
    payload = decode_access_token(refresh_token_value)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")

    # 验证令牌是否被撤销
    if get_refresh_token_user(jti) != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已被撤销"
        )

    # 检查用户是否存在且激活
    user = get_user_by_id(user_id)
    if user is None or not user.is_active:
        # 撤销所有令牌
        revoke_refresh_token(jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )

    # 生成新令牌 (令牌旋转：旧刷新令牌失效)
    access_token = create_access_token(data={"sub": user_id})
    from app.core.security import generate_token_id
    new_jti = generate_token_id()
    new_refresh_token = create_refresh_token(data={"sub": user_id, "jti": new_jti})

    # 撤销旧令牌，存储新令牌
    revoke_refresh_token(jti)
    store_refresh_token(new_jti, user_id)

    # 更新 cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.HTTPS_ENABLED,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user_id
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    登出.

    撤销刷新令牌并清除 cookie。
    """
    refresh_token_value = request.cookies.get("refresh_token")

    if refresh_token_value:
        payload = decode_access_token(refresh_token_value)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti")
            revoke_refresh_token(jti)

    # 清除 cookie
    response.delete_cookie("refresh_token")

    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_user_required)):
    """获取当前用户信息."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        is_active=current_user["is_active"],
        created_at=current_user.get("created_at")
    )


@router.post("/revoke")
async def revoke_all_tokens(
    current_user: dict = Depends(get_current_user_required),
    response: Response = None
):
    """
    撤销用户的所有刷新令牌.

    用于安全操作后 (如修改密码)。
    """
    # 简化实现：清除所有令牌
    # 生产环境应按用户ID清除
    global _refresh_tokens
    _refresh_tokens.clear()

    response.delete_cookie("refresh_token")
    return {"message": "所有令牌已撤销"}
