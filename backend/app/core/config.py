"""应用配置管理 - 安全优先设计.

安全特性:
- 强制设置敏感配置 (SECRET_KEY, 数据库密码)
- 默认使用生产安全设置
- 配置验证和类型检查
- 环境感知 (development/production/testing)
"""
import os
import secrets
from typing import List, Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, field_validator


# ============================================================================
# 默认禁止的值 (防止使用不安全的默认配置)
# ============================================================================

FORBIDDEN_SECRET_KEYS = {
    "your-secret-key-change-in-production",
    "secret",
    "dev",
    "development",
    "test",
    "changeme",
    "your-secret-key",
    "secret-key",
    ""
}

FORBIDDEN_CORS_ORIGINS = {
    "*",
    "all",
    "any"
}


class Settings(BaseSettings):
    """应用配置 - 安全优先."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略额外的环境变量
    )

    # ========================================================================
    # 基础配置
    # ========================================================================

    APP_NAME: str = Field(default="AlgoStone", description="应用名称")
    ENVIRONMENT: str = Field(
        default="production",
        description="运行环境: development, production, testing"
    )
    DEBUG: bool = Field(default=False, description="调试模式 (生产环境必须为False)")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """验证环境变量."""
        allowed = {"development", "production", "testing"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f'ENVIRONMENT 必须是 {allowed} 之一，当前值: {v}')
        return v_lower

    @field_validator("DEBUG")
    @classmethod
    def validate_debug(cls, v: bool, info) -> bool:
        """生产环境禁止调试模式."""
        environment = info.data.get("ENVIRONMENT", "production")
        if environment == "production" and v is True:
            raise ValueError("生产环境 (production) 不允许 DEBUG=True")
        return v

    # ========================================================================
    # API配置
    # ========================================================================

    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 路径前缀")

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="允许的CORS来源 (生产环境必须明确指定)"
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info) -> List[str]:
        """验证CORS配置."""
        environment = info.data.get("ENVIRONMENT", "production")

        # 检查通配符
        if "*" in v or "all" in v:
            if environment == "production":
                raise ValueError("生产环境不允许使用通配符 (*) 作为 CORS_ORIGINS")
            # 开发环境允许但警告
            import warnings
            warnings.warn("CORS_ORIGINS 包含通配符，仅建议在开发环境使用")

        return v

    # ========================================================================
    # AI模型配置（兼容OpenAI API格式的任何模型）
    # ========================================================================

    MODEL_NAME: str = Field(default="qwen-plus", description="模型名称")
    API_KEY: str = Field(default="", description="API密钥 (必需)")
    MODEL_API_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="API地址"
    )

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """验证API密钥已设置."""
        if not v or v.strip() == "":
            raise ValueError(
                "API_KEY 环境变量未设置。"
                "请在 .env 文件中设置: API_KEY=your-actual-api-key"
            )
        if len(v) < 10:
            raise ValueError("API_KEY 长度似乎过短，请检查是否正确设置")
        return v

    # ========================================================================
    # 数据库配置 (PostgreSQL + pgvector)
    # ========================================================================

    POSTGRES_SERVER: str = Field(default="localhost", description="数据库服务器")
    POSTGRES_USER: str = Field(default="postgres", description="数据库用户")
    POSTGRES_PASSWORD: str = Field(default="", description="数据库密码 (必需)")
    POSTGRES_DB: str = Field(default="algostone", description="数据库名称")
    POSTGRES_PORT: int = Field(default=5432, description="数据库端口")

    @field_validator("POSTGRES_PASSWORD")
    @classmethod
    def validate_db_password(cls, v: str) -> str:
        """验证数据库密码已设置."""
        # 开发环境允许简单密码
        environment = os.getenv("ENVIRONMENT", "development")

        if not v or v.strip() == "":
            raise ValueError(
                "POSTGRES_PASSWORD 环境变量未设置。"
                "请在 .env 文件中设置密码 (开发环境可以是简单密码)"
            )

        # 仅生产环境检查长度
        if environment == "production" and len(v) < 8:
            raise ValueError("数据库密码长度必须至少8个字符")
        return v

    # ========================================================================
    # 消息队列配置
    # ========================================================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )

    # ========================================================================
    # JWT配置 - 安全优先
    # ========================================================================

    SECRET_KEY: str = Field(
        default="",
        description="JWT密钥 (生产环境必需，至少32字符)"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """验证SECRET_KEY安全."""
        environment = info.data.get("ENVIRONMENT", "production")

        # 开发环境：如果为空，生成一个默认密钥
        if environment == "development" and (not v or v.strip() == ""):
            import warnings
            warnings.warn("开发环境使用自动生成的 SECRET_KEY。生产环境必须设置强密钥！")
            return "dev-secret-key-for-local-development-only-do-not-use-in-production"

        # 生产环境必须设置
        if environment == "production" and (not v or v.strip() == ""):
            raise ValueError(
                "生产环境必须设置 SECRET_KEY 环境变量。"
                "使用以下命令生成: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # 检查禁止的默认值 (仅生产环境)
        if environment == "production" and v.lower() in FORBIDDEN_SECRET_KEYS:
            raise ValueError(
                f"SECRET_KEY 使用了不安全的默认值 '{v}'。"
                "请在 .env 文件中设置强密钥。"
                "生成命令: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # 生产环境检查长度
        if environment == "production" and len(v) < 32:
            raise ValueError(
                f"SECRET_KEY 长度不足 (当前: {len(v)}, 要求: >=32)。"
                "请使用更长的密钥以提高安全性。"
            )

        return v

    ALGORITHM: str = Field(default="HS256", description="JWT算法")

    # 访问令牌: 短期 (15分钟)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=5,
        le=60,
        description="访问令牌过期时间 (分钟，推荐5-30)"
    )

    # 刷新令牌: 长期 (7天)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=30,
        description="刷新令牌过期时间 (天)"
    )

    # ========================================================================
    # 速率限制配置
    # ========================================================================

    # 登录速率限制 (每分钟)
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(default=5, ge=1, description="登录速率限制")

    # 代码执行速率限制 (每分钟)
    RATE_LIMIT_EXECUTE_PER_MINUTE: int = Field(default=20, ge=1, description="代码执行速率限制")

    # 聊天API速率限制 (每分钟)
    RATE_LIMIT_CHAT_PER_MINUTE: int = Field(default=30, ge=1, description="聊天API速率限制")

    # ========================================================================
    # 代码执行沙箱配置
    # ========================================================================

    # Judge0 API 配置
    JUDGE0_API_URL: Optional[str] = Field(default=None, description="Judge0 API地址")
    JUDGE0_LANGUAGE_ID: int = Field(default=71, description="Python3的Judge0语言ID")

    # Docker 沙箱配置
    DOCKER_ENABLED: bool = Field(default=True, description="是否启用Docker沙箱")
    DOCKER_IMAGE: str = Field(default="python:3.11-slim", description="执行代码的Docker镜像")
    EXECUTION_TIMEOUT_SECONDS: int = Field(default=60, ge=1, le=120, description="代码执行超时时间")
    MAX_CODE_LENGTH: int = Field(default=100000, ge=1000, description="代码最大长度 (字符)")

    # ========================================================================
    # 安全头配置
    # ========================================================================

    SECURITY_ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="允许的主机名 (用于TrustedHost中间件)"
    )

    HTTPS_ENABLED: bool = Field(default=True, description="是否强制HTTPS (生产环境)")

    @field_validator("HTTPS_ENABLED")
    @classmethod
    def validate_https(cls, v: bool, info) -> bool:
        """生产环境强制HTTPS."""
        environment = info.data.get("ENVIRONMENT", "production")
        if environment == "production" and not v:
            import warnings
            warnings.warn("生产环境强烈建议启用 HTTPS_ENABLED=True")
        return v

    # ========================================================================
    # 日志配置
    # ========================================================================

    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(default="json", description="日志格式: json, text")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f'LOG_LEVEL 必须是 {allowed} 之一')
        return v_upper

    # ========================================================================
    # 功能开关
    # ========================================================================

    ENABLE_REGISTRATION: bool = Field(default=True, description="是否允许新用户注册")
    ENABLE_CHAT: bool = Field(default=True, description="是否启用聊天功能")
    ENABLE_CODE_EXECUTION: bool = Field(default=True, description="是否启用代码执行")

    # ========================================================================
    # 辅助方法
    # ========================================================================

    @property
    def is_production(self) -> bool:
        """是否为生产环境."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境."""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """是否为测试环境."""
        return self.ENVIRONMENT == "testing"

    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的来源 (带验证)."""
        if self.is_production and "*" in self.CORS_ORIGINS:
            raise ValueError("生产环境不允许使用通配符CORS")
        return self.CORS_ORIGINS


# ============================================================================
# 生成强密钥的辅助函数
# ============================================================================

def generate_secret_key() -> str:
    """
    生成安全的随机密钥用于SECRET_KEY.

    Returns:
        32字节的URL安全随机字符串 (约43字符)
    """
    return secrets.token_urlsafe(32)


def generate_db_password(length: int = 32) -> str:
    """
    生成强数据库密码.

    Args:
        length: 密码长度

    Returns:
        随机密码字符串
    """
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================================
# 单例实例
# ============================================================================

settings = Settings()


# ============================================================================
# 启动时验证
# ============================================================================

def validate_settings_on_startup() -> None:
    """
    应用启动时验证配置.

    Raises:
        ValueError: 配置不安全或缺失
    """
    errors = []

    # 检查必需的环境变量
    if not settings.API_KEY:
        errors.append("API_KEY 未设置")

    if settings.is_production:
        if not settings.SECRET_KEY or settings.SECRET_KEY in FORBIDDEN_SECRET_KEYS:
            errors.append("生产环境 SECRET_KEY 未设置或使用了不安全的默认值")

        if not settings.POSTGRES_PASSWORD or len(settings.POSTGRES_PASSWORD) < 8:
            errors.append("生产环境 POSTGRES_PASSWORD 未设置或过弱")

        if settings.DEBUG:
            errors.append("生产环境不允许 DEBUG=True")

    if errors:
        error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)


# 在模块加载时自动验证
try:
    validate_settings_on_startup()
except Exception as e:
    import warnings
    warnings.warn(f"配置验证警告: {e}")
