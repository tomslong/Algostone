# AlgoStone 系统使用说明

## 1. 系统简介
AlgoStone 是一个面向大学生的算法学习智能体，提供代码调试、错误诊断、阶梯式提示和算法概念解答等功能。

## 2. 环境要求
- Docker & Docker Compose
- Python 3.10+ (本地开发)
- Node.js 18+ (前端开发)

## 3. 快速启动

### 3.1 使用 Docker Compose 启动（推荐）
在项目根目录下运行：
```bash
docker-compose up -d
```
这将启动以下服务：
- 后端 API: http://localhost:8000
- 数据库 (PostgreSQL): localhost:5432
- 缓存 (Redis): localhost:6379

### 3.2 本地开发启动
1. **启动依赖服务**：
   ```bash
   docker-compose up -d db redis
   ```

2. **启动后端**：
   ```bash
   cd backend
   uv sync  # 安装依赖
   uv run uvicorn app.main:app --reload
   ```

## 4. 功能使用指南

### 4.1 提交代码调试
- **接口**: `POST /api/chat/send`
- **场景**: 当你写好了代码（或部分代码）想验证是否正确，或遇到报错无法解决时。
- **参数**:
  - `message`: "我的代码报错了，帮我看看"
  - `code`: (你的Python代码)
- **系统反馈**:
  - 如果有错误，系统会指出错误类型和原因。
  - 系统不会直接给出修复后的代码，而是通过"阶梯式提示"引导你自己发现问题。

### 4.2 询问算法概念
- **接口**: `POST /api/chat/send`
- **场景**: 遇到不懂的算法名词，如"什么是动态规划？"。
- **参数**:
  - `message`: "什么是动态规划？"
- **系统反馈**:
  - 系统会结合内置知识库（RAG），用通俗易懂的语言解释概念，并提供示例。

### 4.3 获取解题提示
- **接口**: `POST /api/chat/send`
- **场景**: 做题没有思路，需要一点灵感。
- **参数**:
  - `message`: "这道题怎么做？给点提示"
- **系统反馈**:
  - 系统会提供 Level 1 提示（解题思路/算法方向）。
  - 如果仍不明白，再次询问可获取 Level 2（关键步骤）和 Level 3（伪代码）提示。

## 5. 配置说明
配置文件位于 `backend/.env` (可参考 `.env.example`)。
主要配置项：
- `DATABASE_URL`: 数据库连接串
- `OPENAI_API_KEY`: LLM API密钥
- `JUDGE0_API_URL`: 代码沙盒地址

## 6. 题目数据加载
题目数据会存储在 `backend/data/problems.db`（SQLite）中。
如果数据库为空或数量不足，会在首次访问 `/api/problems?limit=XXX` 时自动从 GitHub 的 `merged_problems.json` 拉取数据并写入 SQLite。
默认拉取上限为 500，可通过请求参数 `limit` 调整。

该拉取方式不依赖 GitHub Token，但首次拉取的数据量较大。

建议将 `backend/data` 作为持久化目录保留；如果删除 Docker 数据或挂载目录，题目数据会被清空，需要重新拉取。
也可以手动执行：

```bash
python backend/data/fetch_problems.py
```

## 7. 常见问题
- **Q: 代码执行超时？**
  - A: 检查代码是否有死循环。沙盒默认限制执行时间为 2 秒。
- **Q: 提示不够准确？**
  - A: 尝试更详细地描述你的问题，或者提供相关的题目ID（如果有）。
