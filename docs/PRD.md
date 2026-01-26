# AlgoStone 产品需求文档 (PRD)

| 文档版本 | 修改日期 | 修改人 | 修改内容 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| v1.0 | 2026-01-14 | AlgoStone Team | 初始版本创建 |以此为准 |

---

## 1. 项目概况 (Introduction)

### 1.1 背景
传统的算法学习平台往往直接提供题解，学生在遇到困难时缺乏引导，容易产生依赖心理。AlgoStone 旨在打造一个 AI 驱动的智能算法辅导系统，通过苏格拉底式的引导教学，帮助学生逐步掌握解题思路，而非直接获取答案。

### 1.2 目标
构建一个集"智能辅导"、"代码实践"、"知识检索"于一体的在线学习环境，核心能力包括：
*   **智能引导**：基于 LangGraph 的状态机，提供分层级的解题提示。
*   **安全沙盒**：基于 Judge0 的安全代码执行环境，支持自定义测试用例。
*   **即时反馈**：实时的代码运行结果和错误诊断。

### 1.3 范围
*   **前端**：React + Shadcn UI 构建的现代化交互界面（Unified IDE）。
*   **后端**：FastAPI + LangGraph 构建的业务逻辑与智能体编排。
*   **基础设施**：Judge0 (代码沙盒), PostgreSQL/Vector 存储。

---

## 2. 用户角色 (User Roles)

| 角色 | 描述 | 主要职责/使用场景 |
| :--- | :--- | :--- |
| **学生/开发者** | 算法学习者 | 选择题目、编写代码、与 AI 对话获取提示、运行测试用例。 |
| **管理员** (规划中) | 系统维护者 | 题目管理、用户管理、系统监控。 |

---

## 3. 功能需求 (Functional Requirements)

### 3.1 智能辅导模块 (Intelligent Tutoring)
该模块是系统的核心，负责处理用户与 AI 的交互。

*   **FR-1.1 对话交互**
    *   用户可以在聊天界面发送文本消息和代码片段。
    *   系统需维护对话上下文（Conversation History）。
*   **FR-1.2 意图识别 (Intent Recognition)**
    *   系统需自动识别用户意图：`submit_code` (提交代码), `ask_concept` (询问概念), `request_hint` (请求提示)。
    *   **技术实现**：LangGraph `intent_recognition_node`。
*   **FR-1.3 错误诊断 (Error Diagnosis)**
    *   当用户提交错误代码时，系统自动在沙盒中运行并捕获错误（SyntaxError, IndexError 等）。
    *   **技术实现**：LangGraph `error_diagnosis_node` 调用 Judge0 API。
*   **FR-1.4 阶梯式提示 (Step-wise Hinting)**
    *   系统不直接给出代码，而是根据当前状态提供分级提示：
        *   **Level 1**: 算法方向提示（如"尝试使用双指针"）。
        *   **Level 2**: 关键步骤提示（如"先排序，再遍历"）。
        *   **Level 3**: 伪代码或代码框架。
    *   **技术实现**：LangGraph `stepwise_hint_node` + RAG 检索。
*   **FR-1.5 RAG 知识增强**
    *   针对用户的问题，系统需检索相关算法知识库，提供准确的概念解释。

### 3.2 代码执行模块 (Code Execution)
该模块提供安全、隔离的代码运行环境。

*   **FR-2.1 多语言支持**
    *   当前支持 Python (3.10+)。
    *   架构需预留 Java/C++ 扩展能力 (Judge0 原生支持)。
*   **FR-2.2 安全沙盒**
    *   使用 **Judge0** 作为底层执行引擎。
    *   所有用户代码必须在隔离容器中运行。
    *   限制网络访问 (Judge0 配置)。
    *   限制内存 (256MB) 和执行时间 (2s)。
*   **FR-2.3 自定义测试**
    *   支持用户输入自定义的 Input/Output 用例进行测试。
    *   返回详细的执行结果：Status, Output, Error Message, Execution Time。

### 3.3 学习界面 (Learning Interface)

*   **FR-3.2 统一 IDE 页面 (Unified IDE Page)**
    *   **集成 AI 智能体**：IDE 界面内置智能对话板块 (Chatbot)，实现编程与辅导的无缝衔接。
    *   **三栏布局**：
        *   **左侧**: 题目描述与 AI 助手 (Chatbot) 选项卡。
        *   **中间**: 代码编辑器 (Monaco Editor)。
        *   **右侧**: 测试用例与运行结果面板。
    *   **功能集成**：
        *   支持快捷键运行代码。
        *   AI 助手支持上下文感知的代码纠错与提示。

*   **FR-3.3 设置页面 (Settings Page)**
    *   **API密钥配置**：
        *   支持输入大模型 API Key。
        *   提供显示/隐藏切换、复制、保存功能。
    *   **安全性**：
        *   API Key 后端加密存储。
        *   前端默认显示掩码 (*******)。
    *   **验证功能**：
        *   格式校验。
        *   "测试连接" 按钮验证 Key 有效性。
        *   显示详细验证结果。
    *   **扩展性**：预留其他模型参数配置位.

*   **FR-3.4 用户个人中心 (User Profile)**
    *   **用户信息管理**：
        *   基本信息：用户名（可编辑）、头像（支持上传/修改）、邮箱（支持验证修改）。
        *   安全设置：密码修改（需旧密码验证）。
    *   **API Key 管理 (移动端/简化版)**：
        *   浏览器 localStorage 安全存储。
        *   支持生成唯一 Key、查看、复制、重置。
        *   安全保障：防止意外网络上传。
    *   **学习活动可视化**：
        *   **Activity Calendar**：类 GitHub 贡献图。
        *   维度：按天显示聊天/做题活跃度。
        *   交互：颜色深浅表示活跃度，Hover 显示详情，支持时间范围切换（周/月/年）。

*   **FR-3.5 消息/题目列表过滤 (Filter System)**
    *   **Sidebar 过滤**：
        *   规则：按难度 (Easy/Medium/Hard)、状态 (Solved/Unsolved)、标签过滤。
    *   **交互要求**：
        *   点击 Filter 按钮显示过滤面板。
        *   立即应用过滤条件并反馈（Filter Enabled 状态）。
        *   提供清除按钮。
        *   状态持久化（localStorage）。

---

## 4. 非功能需求 (Non-Functional Requirements)

### 4.1 性能要求
*   **响应时间**：
    *   代码执行 API (`/api/execute`)：< 3秒 (包含容器启动)。
    *   对话 API (`/api/chat/send`)：首字响应 < 2秒 (建议流式，目前为全量返回)。
*   **并发能力**：支持至少 50 个并发沙盒实例。

### 4.2 安全性
*   **代码隔离**：严格防止恶意代码逃逸（如 `os.system('rm -rf')`）。
*   **输入校验**：所有 API 输入需经过 Pydantic 模型校验。

### 4.3 兼容性
*   **前端**：支持 Chrome, Firefox, Safari, Edge 最新版本。
*   **后端**：Python 3.10+ 环境。

---

## 5. 系统架构 (System Architecture)

### 5.1 技术栈
*   **Frontend**: React, TypeScript, Vite, TailwindCSS, Shadcn UI.
*   **Backend**: FastAPI, Pydantic v2.
*   **Message Queue**: Redis + Celery (异步任务处理).
*   **AI/Agent**: LangGraph (状态机), LangChain, OpenAI/Qwen API.
*   **Database**: PostgreSQL + pgvector (业务数据与向量数据).
*   **Infrastructure**: Judge0 (代码沙盒), Docker (服务部署).

### 5.2 数据流向
1.  **用户**在前端发送消息/代码。
2.  **FastAPI** 接收请求，路由至 `Chat` 或 `Execute` 模块。
3.  **Chat 模块** 启动 LangGraph 状态机：
    *   调用 **LLM** 进行意图分析。
    *   如需执行，调用 **Execute 模块**。
    *   如需知识，检索 **Vector Store (pgvector)**。
4.  **Execute 模块** 调用 **Judge0 API** 运行代码，返回结果。
5.  最终响应返回前端渲染。

---

## 6. 数据模型与接口 (Data Models & API)

### 6.1 核心数据结构
与后端 `schemas.py` 保持严格一致。

#### ChatRequest
```json
{
  "message": "string (用户消息)",
  "code": "string? (可选代码)",
  "problem_id": "string? (题目ID)",
  "conversation_history": [
    { "role": "user|assistant", "content": "string" }
  ]
}
```

#### ChatResponse
```json
{
  "message": "string (AI回复)",
  "hint_level": "int (1-3)",
  "intent": "string (submit_code|ask_concept...)",
  "code_execution_result": {
    "status": "success|error",
    "output": "string",
    "error_message": "string"
  }
}
```

#### CodeExecutionRequest
```json
{
  "code": "string (完整代码)",
  "language": "string (default: python)",
  "test_cases": [
    { "input": "string", "expected_output": "string" }
  ]
}
```

### 6.2 接口定义
详细接口文档请参考 [API.md](./API.md)。
*   `POST /api/chat/send`: 发送对话。
*   `POST /api/execute`: 执行代码。
*   `GET /api/health`: 系统健康检查。

### 6.3 API 文档自动化
*   **Swagger/OpenAPI**: 后端基于 FastAPI 自动生成符合 OpenAPI 3.0 标准的接口文档。
    *   交互式文档地址: `/docs` (Swagger UI)
    *   静态文档地址: `/redoc`
*   **MkDocs 集成**: 项目整体文档使用 MkDocs 构建，需集成 OpenAPI 规范，实现技术文档与接口定义的一体化展示。

---

## 7. 测试与验收标准 (Acceptance Criteria)

### 7.1 智能体验收
*   [ ] **意图识别准确率**：> 90%。能准确区分"帮我改代码"和"解释动态规划"。
*   [ ] **提示层级有效性**：在 Level 1 不应泄露具体代码，在 Level 3 应提供具体框架。
*   [ ] **错误诊断**：能正确识别常见的 Python 错误（SyntaxError, IndexError, RecursionError）并给出友好解释。

### 7.2 沙盒验收
*   **安全性**：禁止网络请求代码执行成功；禁止文件系统写操作（Judge0 限制）。
*   **准确性**：正确代码返回 Success，错误代码返回 Error。
*   **超时控制**：死循环代码应在 2秒内被 Kill 并返回 Timeout。

### 7.3 前端验收
*   [ ] **交互流畅**：聊天气泡显示正常，代码高亮正确。
*   [ ] **响应反馈**：API 请求期间显示 Loading 状态。
