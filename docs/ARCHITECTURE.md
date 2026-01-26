# AlgoStone 架构设计文档

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                             │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   首页       │  │   统一IDE    │                        │
│  │  HomePage    │  │   IDEPage    │                        │
│  └──────────────┘  └──────────────┘                        │
│            React + TypeScript + Shadcn UI                    │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                        API网关层                             │
│                       FastAPI Routes                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  /chat/send  │  │ /chat/execute│  │  /health     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      业务逻辑层                              │
│                   LangGraph State Machine                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 意图识别节点  │→│ 错误诊断节点  │→│ 提示生成节点  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                          ↓                   │
│                                  ┌──────────────┐            │
│                                  │ 代码对比节点  │            │
│                                  └──────────────┘            │
└─────────────────────────────────────────────────────────────┘
              ↕                ↕                ↕
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   RAG模块       │  │  代码沙盒模块    │  │   LLM模块       │
│                 │  │                 │  │                 │
│ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
│ │ VectorStore │ │  │ │  Executor   │ │  │ │  Qwen-8B    │ │
│ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │
│ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
│ │  Retriever  │ │  │ │ TestRunner  │ │  │ │  Prompts    │ │
│ └─────────────┘ │  │ └─────────────┘ │  │ └─────────────┘ │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        ↕                    ↕
┌─────────────────┐  ┌─────────────────┐
│  PostgreSQL     │  │  Judge0 Service │
│   + pgvector    │  │   代码沙盒      │
└─────────────────┘  └─────────────────┘
```

---

## 核心模块详解

### 1. LangGraph状态机

**作用**: 编排整个对话流程，确保Agent以引导式而非直接回答的方式帮助学生。

**状态定义** (`backend/langgraph_agent/state.py`):
```python
class AgentState(TypedDict):
    session_id: str
    user_message: str
    user_code: Optional[str]
    intent: Optional[IntentType]
    has_error: bool
    current_hint_level: int
    # ... 更多状态字段
```

**节点流程**:
1. **意图识别** (`intent_recognition_node`)
   - 输入: 用户消息 + 代码（可选）
   - 输出: 意图类型（提交代码/询问概念/请求提示）
   
2. **错误诊断** (`error_diagnosis_node`)
   - 条件: 仅当意图为"提交代码"时执行
   - 操作: 调用代码沙盒执行代码
   - 输出: 错误类型、错误信息、执行结果
   
3. **阶梯式提示** (`stepwise_hint_node`)
   - 输入: 当前提示级别、RAG检索结果
   - 操作: 调用LLM生成引导式提示
   - 输出: 提示内容、新的提示级别
   
4. **代码对比** (`code_comparison_node`)
   - 条件判断: 是否需要更多提示 or 问题已解决
   - 输出: 流程控制信号（继续/结束）

**状态转移规则**:
- 最多3轮提示循环
- 代码通过测试 → 结束并鼓励
- 达到最大提示次数 → 建议查看完整题解

---

### 2. RAG知识库

**Parent Document Retrieval策略**:

```
原始题解（长文档）
    ↓ 切分
┌─────────────────┐
│  Parent Chunk   │ (1000字符)
│ "动态规划解法..."│
└─────────────────┘
    ↓ 再切分
┌───────┐ ┌───────┐ ┌───────┐
│Child 1│ │Child 2│ │Child 3│ (200字符)
└───────┘ └───────┘ └───────┘
    ↓ 向量化存储
  PostgreSQL (pgvector)
    ↓ 检索时
   找到Child → 返回完整Parent
```

**优势**:
- 检索精度高（小chunk更准确匹配）
- 上下文完整（返回大chunk保证信息完整性）

**实现** (`backend/rag/retriever.py`):
```python
class ParentDocumentRetriever:
    def retrieve(self, query: str) -> List[Dict]:
        # 1. 检索child chunks
        child_results = vector_store.search(query)
        
        # 2. 提取parent文档并去重
        parent_docs = {}
        for child_id in child_results['ids']:
            parent_id = self.parent_child_map[child_id]
            parent_docs[parent_id] = ...
        
        return sorted_parents
```

---

### 3. 代码沙盒

**安全隔离方案**:
- Docker容器（`python:3.10-slim`镜像）
- 资源限制: 2秒超时、256MB内存
- 网络隔离: `network_disabled=True`

**执行流程**:
```python
# 1. 构建测试代码
full_code = f"""
{user_code}

# 注入测试用例
test_cases = {test_cases}
# 执行并比对结果
...
"""

# 2. 在容器中运行
container.run(
    image='python:3.10-slim',
    command=f'python -c "{full_code}"',
    mem_limit='256m',
    network_disabled=True
)

# 3. 捕获输出和错误
```

**错误类型映射** (`backend/sandbox/test_runner.py`):
- `IndexError` → "数组越界"
- `RecursionError` → "递归深度超限"
- `KeyError` → "字典键不存在"
- ...

---

### 4. Prompt工程

**Few-shot示例结构** (`backend/prompts/few_shot_examples.json`):
```json
{
  "scenario": "数组越界错误",
  "student_code": "...",
  "error": "IndexError: ...",
  "agent_response": "引导式提示...",
  "student_fixed_code": "..."
}
```

**CoT思维链模板** (`backend/prompts/cot_templates.py`):
```
步骤1: 理解学生代码的整体逻辑
步骤2: 定位具体错误
步骤3: 思考引导方式（不直接给答案）
步骤4: 生成引导式反馈
```

**提示级别设计**:
- Level 1: 算法方向（"考虑使用哈希表"）
- Level 2: 关键步骤（"先遍历数组，记录每个数"）
- Level 3: 伪代码框架（"for num in nums: ..."）

---

## 数据流示例

### 场景: 学生提交错误代码

```
1. 用户提交代码
   ↓
2. API接收: POST /api/chat/send
   {
     "message": "我的代码不work",
     "code": "def twoSum(nums, target): ..."
   }
   ↓
3. LangGraph启动
   ↓
4. 意图识别节点
   → 识别为 "submit_code"
   ↓
5. 错误诊断节点
   → 调用 CodeExecutor
   → Docker容器执行代码
   → 捕获: IndexError
   ↓
6. 阶梯式提示节点
   → RAG检索相关知识
   → 调用Qwen-8B (with CoT)
   → 生成: "我注意到你的代码在某些情况下..."
   ↓
7. 代码对比节点
   → 判断: 未通过，且未达最大提示次数
   → 决策: 可以继续提示
   ↓
8. 返回响应
   {
     "message": "引导式提示...",
     "hint_level": 1,
     "code_execution_result": {...}
   }
```

---

## 扩展性考虑

### 1. 多语言支持
当前仅支持Python，扩展方案：
- 利用 Judge0 的多语言支持 (C++, Java, Go等)
- 只需修改 `language_id` 参数
- 统一错误解析逻辑

### 2. 自定义题库
- 管理员上传题目接口
- 题目审核机制
- 难度自动评估

### 3. 学习路径推荐
- 记录学生做题历史
- 分析薄弱知识点
- 推荐相似题目

---

## 性能优化

### 1. 向量检索优化
- 使用量化索引（IVF）
- 缓存热门查询结果
- 定期清理过期索引

### 2. LLM调用优化
- Streaming响应
- 结果缓存（相同问题24小时内复用）
- 批量请求合并

### 3. 代码执行优化
- Judge0 实例水平扩展
- 简单测试用例本地执行
- 提交请求使用 `wait=false` 异步轮询

---

## 监控与日志

### 关键指标
- API响应时间
- LangGraph每个节点耗时
- 代码执行成功率
- RAG检索命中率
- LLM token消耗

### 日志策略
- 结构化日志（JSON格式）
- 按会话ID关联所有日志
- 敏感信息脱敏

---

## 安全考虑

### 1. 代码沙盒安全
- ✅ Docker隔离
- ✅ 资源限制
- ✅ 网络隔离
- ⚠️ TODO: 文件系统只读

### 2. API安全
- ⚠️ TODO: 添加认证（JWT）
- ⚠️ TODO: 限流（防止滥用）
- ⚠️ TODO: 输入验证和清洗

### 3. 数据安全
- ⚠️ TODO: 学生代码加密存储
- ⚠️ TODO: 对话历史定期清理
- ⚠️ TODO: GDPR合规

---

## 部署架构

### 开发环境
```
localhost:3000 (Frontend)
localhost:8000 (Backend)
localhost:5432 (PostgreSQL)
localhost:6379 (Redis)
```

### 生产环境（建议）
```
┌──────────────┐
│  Nginx       │ ← SSL终止 + 负载均衡
└──────────────┘
       ↓
┌──────────────┐
│  Frontend    │ (静态文件 CDN)
│  Container   │
└──────────────┘
       ↓
┌──────────────┐
│  Backend     │ (多实例)
│  Container   │
└──────────────┘
       ↓
┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │
└──────────────┘  └──────────────┘
```
