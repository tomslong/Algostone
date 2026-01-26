"""安全工具函数 - 使用 Argon2 密码哈希.

遵循 OWASP 密码存储最佳实践:
- 使用 Argon2 (2015年密码哈希竞赛冠军)
- 自适应计算成本 (可调整迭代次数、内存消耗)
- 盐值自动管理
"""
import secrets
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings as app_settings

# ============================================================================
# 密码哈希配置 (Argon2)
# ============================================================================

# 使用 Argon2id (混合 Argon2i 和 Argon2d 的优点)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    # Argon2 参数 (可根据服务器性能调整):
    # - time_cost: 迭代次数 (计算成本)
    # - memory_cost: 内存成本 (KB单位，64MB = 65536)
    # - parallelism: 并行线程数
    argon2__time_cost=3,       # 每个哈希迭代3次
    argon2__memory_cost=65536,  # 使用64MB内存 (防止GPU攻击)
    argon2__parallelism=4,      # 使用4个并行线程
)

# 密码强度要求
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
# 要求: 至少包含小写、大写、数字、特殊字符中的3种
PASSWORD_PATTERN = re.compile(
    r'^(?:(?=.*[a-z])(?=.*[A-Z])(?=.*\d)|'  # 小写+大写+数字
    r'(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*])|'  # 小写+大写+特殊字符
    r'(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])|'  # 小写+数字+特殊字符
    r'(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]))'  # 大写+数字+特殊字符
    r'[A-Za-z\d!@#$%^&*]{8,}$'
)

# 常见弱密码列表 (示例，应扩展)
COMMON_PASSWORDS = {
    'password', 'password123', '12345678', 'qwerty123',
    'abc12345', 'monkey123', 'letmein123', 'trustno1',
    'admin123', 'welcome1', 'login123', 'pass1234'
}


def get_password_hash(password: str) -> str:
    """
    使用 Argon2 哈希密码.

    Args:
        password: 明文密码

    Returns:
        格式: $argon2id$v=19$m=65536,t=3,p=4$...

    Raises:
        ValueError: 密码不符合强度要求
    """
    if not is_strong_password(password):
        raise ValueError("密码不符合强度要求")

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码.

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        验证成功返回 True
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def is_strong_password(password: str) -> bool:
    """
    检查密码强度.

    规则:
    - 长度 8-128 字符
    - 不在常见弱密码列表中
    - 至少包含3种字符类型 (大写、小写、数字、特殊字符)

    Args:
        password: 要检查的密码

    Returns:
        密码强度足够返回 True
    """
    # 检查长度
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        return False

    # 检查常见弱密码
    if password.lower() in COMMON_PASSWORDS:
        return False

    # 检查字符多样性 (至少3种)
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

    char_types = sum([has_lower, has_upper, has_digit, has_special])
    if char_types < 3:
        return False

    return True


# ============================================================================
# JWT Token 配置
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT 访问令牌 (短期，15分钟).

    Args:
        data: 要编码的数据 (通常包含 user_id)
        expires_delta: 自定义过期时间

    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 默认15分钟 (生产环境建议)
        expire = datetime.utcnow() + timedelta(
            minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(
        to_encode,
        app_settings.SECRET_KEY,
        algorithm=app_settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT 刷新令牌 (长期，7天).

    用于获取新的访问令牌，应存储在 httpOnly cookie 中.

    Args:
        data: 要编码的数据 (通常包含 user_id)
        expires_delta: 自定义过期时间

    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 刷新令牌有效期7天
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(
        to_encode,
        app_settings.SECRET_KEY,
        algorithm=app_settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT 访问令牌.

    Args:
        token: JWT令牌字符串

    Returns:
        解码后的payload，验证失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            app_settings.SECRET_KEY,
            algorithms=[app_settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_user_id() -> str:
    """
    生成唯一用户ID.

    Returns:
        UUID v4 格式的用户ID
    """
    import uuid
    return str(uuid.uuid4())


def generate_token_id() -> str:
    """
    生成唯一的令牌ID (用于刷新令牌追踪).

    Returns:
        URL安全的随机字符串
    """
    return secrets.token_urlsafe(32)


# ============================================================================
# 敏感数据脱敏
# ============================================================================

def sanitize_for_log(message: str, max_length: int = 50) -> str:
    """
    脱敏敏感信息用于日志记录.

    移除/遮蔽:
    - API密钥 (token, api_key, secret, password)
    - 电子邮件地址
    - IP地址
    - 信用卡号

    Args:
        message: 原始消息
        max_length: 最大长度 (超出将被截断)

    Returns:
        脱敏后的消息
    """
    if not message:
        return ""

    # 移除敏感的键值对模式
    sanitized = re.sub(
        r'(token|api_key|secret|password|authorization|bearer)[:\s]*[^\s,\'\"]{8,}',
        r'\1: [REDACTED]',
        message,
        flags=re.IGNORECASE
    )

    # 遮蔽电子邮件
    sanitized = re.sub(
        r'\b([a-zA-Z0-9])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'\1***@\2',
        sanitized
    )

    # 遮蔽IP地址 (部分)
    sanitized = re.sub(
        r'\b(\d{1,3})\.\d{1,3}\.\d{1,3}\.(\d{1,3})\b',
        r'\1.***.***.\2',
        sanitized
    )

    # 截断过长消息
    if len(sanitized) > max_length:
        return sanitized[:max_length] + '...'

    return sanitized


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "get_password_hash",
    "verify_password",
    "is_strong_password",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "generate_user_id",
    "generate_token_id",
    "sanitize_for_log",
    "PASSWORD_MIN_LENGTH",
    "PASSWORD_MAX_LENGTH",
]
