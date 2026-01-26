# AlgoStone

> 智能算法学习助手 - 基于 LangGraph 和 AI 的算法刷题平台

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11-yellow?logo=python)](https://www.python.org)

---

## 简介

AlgoStone 是一个面向算法学习者的智能刷题平台，通过 AI 对话式引导帮助用户深度理解算法思维，而不是简单地给出答案。

---

## 特性

- **AI 智能助手** - 基于用户配置的 LLM API，提供个性化学习指导
- **在线代码执行** - Piston 沙箱安全隔离，支持 Python 代码实时运行
- **题目管理** - LeetCode 风格的算法题库，支持 Easy/Medium/Hard 分类
- **进度追踪** - 自动保存代码，AC 状态实时显示
- **响应式设计** - 现代化 IDE 界面，可调节的侧边栏和面板布局
- **性能优化** - Monaco Editor 懒加载，React.memo 优化

---

## 技术栈

### 后端

- **FastAPI** - 现代异步 Python Web 框架
- **PostgreSQL + pgvector** - 数据库
- **Redis** - 缓存和速率限制
- **Piston** - 代码执行沙箱（Docker 部署）
- **Pydantic** - 数据验证
- **Slowapi** - 速率限制

### 前端

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Monaco Editor** - 代码编辑器
- **Tailwind CSS** - 样式
- **shadcn/ui** - UI 组件库

---

## 快速开始

### 前置要求

- Docker Desktop (推荐) 或 Python 3.11+ / Node.js 18+
- PostgreSQL 16+
- Redis (可选)

### 启动 Piston 代码执行服务

```bash
# 进入 Piston 目录
cd piston

# 启动 Piston 容器
docker-compose up -d

# 验证 Piston 运行状态
curl http://localhost:27123/api/v2/runtimes
```

### 使用 Docker Compose (推荐)

```bash
# 克隆项目
git clone https://github.com/yourusername/algostone.git
cd algostone

# 启动所有服务
docker-compose up -d

# 访问前端
open http://localhost:3001
```

### 本地开发

**后端 (FastAPI)**

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动后端
uvicorn app.main:app --reload --port 8001
```

**前端 (React + Vite)**

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

---

## 项目结构

```
algostone/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   └── routes/        # chat, execute, problems, user...
│   │   ├── core/              # 配置、数据库、安全
│   │   ├── models/            # Pydantic 模型
│   │   └── main.py            # 应用入口
│   ├── sandbox/               # Piston 执行器封装
│   └── requirements.txt
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── ide/           # IDE 组件
│   │   │   └── ui/            # shadcn/ui 组件
│   │   ├── contexts/          # React Context
│   │   └── lib/               # 工具函数
│   └── package.json
│
├── docs/                       # 文档
├── docker-compose.yml
└── README.md

# Piston 服务 (独立部署)
../piston/                      # Piston 代码执行服务
├── docker-compose.yaml         # 容器配置
└── data/piston/packages/       # Python 运行时缓存
```

---

## API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/problems` | 获取题目列表 |
| GET | `/api/v1/problems/{task_id}` | 获取题目详情 |
| POST | `/api/v1/execute` | 执行代码 |
| POST | `/api/v1/submit` | 提交代码 |
| POST | `/api/v1/chat/stream` | AI 对话 (流式) |
| GET | `/api/v1/user/ac-problems/{device_id}` | 获取已通过题目 |

详细 API 文档：`http://localhost:8001/docs` (开发环境)

---

## 环境变量

### 后端 (.env)

```bash
# 数据库
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=algostone

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# 安全
SECRET_KEY=your-secret-key
ENVIRONMENT=development

# API 限制
RATE_LIMIT_CHAT_PER_MINUTE=30
RATE_LIMIT_EXECUTE_PER_MINUTE=60

# 代码执行
EXECUTION_TIMEOUT_SECONDS=60  # 代码执行超时时间 (秒)
MAX_CODE_LENGTH=100000        # 代码最大长度 (字符)
```

### Piston 配置 (piston/docker-compose.yaml)

```bash
PISTON_RUN_TIMEOUT=60000      # 最大运行超时 (毫秒)
PISTON_OUTPUT_MAX_SIZE=10240  # 最大输出大小 (KB)
```

---

## 使用指南

详细使用文档请参阅 [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

---

## 常见问题

**Q: 代码执行失败 / 502 错误？**
> 确保 Piston 服务已启动：`cd ../piston && docker-compose up -d`
>
> 端口冲突？修改 `piston/docker-compose.yaml` 中的端口映射

**Q: AI 对话无响应？**
> 在前端设置页面配置正确的 OpenAI API Key 和 Base URL

**Q: 题目加载不出来？**
> 检查后端服务是否正常运行，数据库是否有题目数据

**Q: 测试用例输出超限？**
> Piston 默认输出限制为 1MB，可在 `piston/docker-compose.yaml` 中调整 `PISTON_OUTPUT_MAX_SIZE`

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License
