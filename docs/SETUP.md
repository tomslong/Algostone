# AlgoStone 开发环境搭建指南

## 前置要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Git
- PostgreSQL 14+ (with pgvector extension)

---

## 快速开始

### 方法1: 使用 Docker Compose（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd AlgoStone
```

2. **配置环境变量**
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

3. **启动所有服务**
```bash
docker-compose up
```

4. **访问应用**
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

---

### 方法2: 本地开发

#### 后端设置

1. **进入后端目录**
```bash
cd backend
```

2. **使用 uv 管理依赖**
```bash
uv sync
```

3. **激活虚拟环境**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. **启动后端**
```bash
uvicorn app.main:app --reload
```

#### 前端设置

1. **进入前端目录**
```bash
cd frontend
```

2. **安装依赖**
```bash
pnpm install
```

3. **启动前端**
```bash
pnpm start
```

---

# 安全配置指南

## 重要: 生产环境必须完成的安全配置

### 1. 生成安全密钥

**生成 JWT SECRET_KEY** (至少32字符):
```bash
python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')"
```

**生成数据库密码** (强密码):
```bash
python -c "import secrets, string; alphabet = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(alphabet) for _ in range(32)))"
```

### 2. 配置 .env 文件

复制配置模板并填写:
```bash
cd backend
cp .env.example .env
```

**必须修改的关键配置**:

```bash
# 运行环境 - 生产环境设为 production
ENVIRONMENT=production
DEBUG=false

# 安全密钥 (使用上面生成的值)
SECRET_KEY=your-generated-secret-key-here

# 数据库强密码
POSTGRES_PASSWORD=your-strong-database-password-here

# API密钥
API_KEY=your-llm-api-key-here
```

### 3. 密码哈希配置

系统使用 **Argon2id** 密码哈希算法 (OWASP推荐):

- time_cost: 3 (迭代次数)
- memory_cost: 65536 (64MB内存，防止GPU攻击)
- parallelism: 4 (并行线程)

**密码强度要求**:
- 长度: 8-128 字符
- 必须包含以下3种字符类型:
  - 大写字母 (A-Z)
  - 小写字母 (a-z)
  - 数字 (0-9)
  - 特殊字符 (!@#$%^&*)

### 4. JWT 令牌配置

**访问令牌** (短期):
- 有效期: 15分钟 (可配置 5-60分钟)
- 用于API认证
- 存储在内存/localStorage

**刷新令牌** (长期):
- 有效期: 7天 (可配置)
- 用于获取新的访问令牌
- 存储在 httpOnly cookie (防XSS)
- 支持令牌旋转 (旧令牌自动失效)

### 5. 代码执行沙箱

**Docker 沙箱隔离** (推荐):
```bash
# 确保Docker运行
docker --version

# 拉取基础镜像
docker pull python:3.11-slim
```

**沙箱安全特性**:
- 禁用网络访问 (`--network=none`)
- 限制内存 (128MB)
- 限制CPU (0.5核)
- 只读根文件系统
- 非特权用户运行
- 禁止提权 (`--security-opt=no-new-privileges`)

**配置项**:
```bash
DOCKER_ENABLED=true
EXECUTION_TIMEOUT_SECONDS=5
MAX_CODE_LENGTH=10000
```

### 6. 速率限制

默认限制 (可配置):

| 端点 | 限制 |
|------|------|
| 登录/注册 | 5次/分钟 |
| 代码执行 | 20次/分钟 |
| 聊天API | 30次/分钟 |

### 7. CORS 配置

**开发环境**:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**生产环境** (必须明确指定):
```bash
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**禁止生产环境使用通配符** (`*`)

### 8. 安全响应头

系统自动添加以下安全头:

| 头 | 值 | 说明 |
|-----|-----|------|
| X-Content-Type-Options | nosniff | 防止MIME类型嗅探 |
| X-Frame-Options | DENY | 防止点击劫持 |
| X-XSS-Protection | 1; mode=block | XSS保护 |
| Strict-Transport-Security | max-age=31536000 | 强制HTTPS |
| Content-Security-Policy | (CSP策略) | 内容安全策略 |

### 9. 日志脱敏

敏感信息自动脱敏:
- API密钥/token → `[REDACTED]`
- 邮箱 → `a***@domain.com`
- IP地址 → `192.***.***.1`

### 10. HTTPS 配置

**生产环境强制HTTPS**:
```bash
HTTPS_ENABLED=true
```

使用反向代理 (Nginx/Caddy) 配置SSL:
```nginx
# Nginx 示例
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 完整 .env 配置示例

```bash
# ============================================================================
# 基础配置
# ============================================================================
ENVIRONMENT=production
DEBUG=false

# ============================================================================
# 安全配置 (必须设置!)
# ============================================================================
SECRET_KEY=your-generated-secret-key-here

# ============================================================================
# AI 模型配置
# ============================================================================
MODEL_NAME=qwen-plus
API_KEY=your-api-key-here
MODEL_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# ============================================================================
# 数据库配置
# ============================================================================
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-strong-database-password-here
POSTGRES_DB=algostone

# ============================================================================
# Redis 配置
# ============================================================================
REDIS_URL=redis://localhost:6379/0

# ============================================================================
# JWT 配置
# ============================================================================
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================================================
# 速率限制
# ============================================================================
RATE_LIMIT_LOGIN_PER_MINUTE=5
RATE_LIMIT_EXECUTE_PER_MINUTE=20
RATE_LIMIT_CHAT_PER_MINUTE=30

# ============================================================================
# 代码执行沙箱
# ============================================================================
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com
JUDGE0_LANGUAGE_ID=71
DOCKER_ENABLED=true
EXECUTION_TIMEOUT_SECONDS=5
MAX_CODE_LENGTH=10000

# ============================================================================
# 安全头
# ============================================================================
SECURITY_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
HTTPS_ENABLED=true

# ============================================================================
# CORS (生产环境必须明确域名)
# ============================================================================
CORS_ORIGINS=https://yourdomain.com

# ============================================================================
# 日志
# ============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================================================
# 功能开关
# ============================================================================
ENABLE_REGISTRATION=true
ENABLE_CHAT=true
ENABLE_CODE_EXECUTION=true
```

---

## 安全检查清单

部署前检查:

- [ ] 已生成强 SECRET_KEY (≥32字符)
- [ ] 已设置强数据库密码 (≥8字符)
- [ ] ENVIRONMENT 设为 "production"
- [ ] DEBUG 设为 false
- [ ] CORS_ORIGINS 明确指定域名 (不含通配符)
- [ ] HTTPS_ENABLED 设为 true
- [ ] Docker 已安装并运行
- [ ] API_KEY 已配置
- [ ] 速率限制已启用
- [ ] 数据库连接正常

---

## 数据准备

### 爬取LeetCode题目

```bash
cd backend
python scripts/run_crawler.py
```

### 建立向量索引

```bash
python scripts/init_db.py
```

---

## 运行测试

### 后端测试
```bash
cd backend
pytest
```

### 前端测试
```bash
cd frontend
pnpm test
```

---

## 常见问题

### 1. Docker容器启动失败
- 确保Docker Desktop正在运行
- 检查端口是否被占用
- 尝试 `docker-compose down -v` 清理后重新启动

### 2. 数据库连接失败
- 检查 PostgreSQL 服务是否启动
- 确认 `.env` 配置正确
- 确认 pgvector 扩展已安装

### 3. 配置验证失败
- 确保 SECRET_KEY ≥ 32字符
- 确保 POSTGRES_PASSWORD ≥ 8字符
- 检查是否有使用默认禁止的值

---

## 下一步

- 阅读 [API文档](./api.md)
- 查看 [架构设计](./ARCHITECTURE.md)
- 了解 [用户指南](./USER_GUIDE.md)
