# AlgoStone API 使用指南

> 本文档面向开发者，介绍如何通过 API 与 AlgoStone 系统交互。

**环境搭建请参考** [SETUP.md](./SETUP.md)

---

## API 基础信息

```
Base URL: http://localhost:8001
API Prefix: /api/v1
Content-Type: application/json
```

---

## 1. 流式聊天接口

### 接口信息

```
POST /api/v1/chat/stream
```

### 功能

与 AI 助手进行对话，支持流式响应（SSE）。支持代码调试、概念询问、阶梯提示等功能。

### 请求参数

```json
{
  "message": "我的代码报错了，帮我看看",
  "code": "def twoSum(nums, target):\n    ...",
  "language": "python",
  "problem_id": "two-sum",
  "session_id": "optional-session-id",
  "conversation_history": [],
  // 可选：动态 LLM 配置（覆盖后端默认配置）
  "api_key": "your-api-key",
  "model_name": "deepseek-reasoner",
  "api_base": "https://api.deepseek.com/v1"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息 |
| code | string | 否 | 用户代码（有代码时触发执行） |
| language | string | 否 | 编程语言，默认 `python` |
| problem_id | string | 否 | 关联的题目ID |
| session_id | string | 是 | 会话ID |
| conversation_history | list | 否 | 对话历史 |
| api_key | string | 否 | 自定义 LLM API Key |
| model_name | string | 否 | 自定义模型名称 |
| api_base | string | 否 | 自定义 API 地址 |

### 响应格式 (Server-Sent Events)

```
data: {"type": "start", "session_id": "xxx"}

data: {"type": "intent", "intent": "submit_code"}

data: {"type": "diagnosis", "has_error": true, "error_type": "IndexError"}

data: {"type": "reasoning", "content": "思考过程..."}  # DeepSeek-R1 等推理模型

data: {"type": "content", "content": "回复片段"}

data: {"type": "end"}
```

### 使用示例

#### cURL

```bash
curl -N http://localhost:8001/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "什么是动态规划？",
    "session_id": "test-session"
  }'
```

#### Python

```python
import requests
import json

url = "http://localhost:8001/api/v1/chat/stream"
data = {
    "message": "我的代码报错了",
    "code": "def twoSum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i+1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]",
    "language": "python",
    "session_id": "test-session"
}

with requests.stream("POST", url, json=data) as response:
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            event = json.loads(line[6:])
            print(event)
```

#### JavaScript

```javascript
const response = await fetch('http://localhost:8001/api/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: '我的代码报错了',
    code: 'def twoSum(nums, target): ...',
    language: 'python',
    session_id: 'test-session'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      console.log(event);
    }
  }
}
```

---

## 2. 非流式聊天

### 接口信息

```
POST /api/v1/chat/send
```

### 功能

非流式聊天接口，等待完整响应后返回。

### 请求参数

与流式接口相同，但不需要 `conversation_history`（可选）。

### 响应示例

```json
{
  "message": "AI回复内容",
  "hint_level": 1,
  "code_execution_result": null,
  "suggested_resources": [],
  "intent": "submit_code"
}
```

---

## 3. 单次代码执行

### 接口信息

```
POST /api/execute
```

### 功能

执行代码并返回结果，不涉及 AI 对话。

### 请求参数

```json
{
  "code": "print('Hello World')",
  "language": "python",
  "test_cases": []
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 要执行的代码 |
| language | string | 否 | 编程语言，默认 `python` |
| test_cases | array | 否 | 测试用例 |

### 响应示例

```json
{
  "status": "success",
  "output": "Hello World\n",
  "error_type": null,
  "error_message": null,
  "execution_time": 0.12
}
```

---

## 4. 提交所有测试用例

### 接口信息

```
POST /api/v1/submit
```

### 功能

运行所有测试用例，判断代码是否通过。

### 请求参数

```json
{
  "code": "def solution(): ...",
  "language": "python",
  "test_cases": [
    {"input": "", "expected_output": "result"}
  ]
}
```

### 响应示例

```json
{
  "status": "success",
  "output": "Case 1: ✓ Passed\nCase 2: ✓ Passed\n\n2/2 test cases passed\n\n🎉 All tests passed!",
  "execution_time": 0.25
}
```

---

## 5. 题目列表

### 接口信息

```
GET /api/v1/problems
```

### 功能

获取算法题列表。

### 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| limit | int | 返回数量，默认 50 |
| offset | int | 偏移量，默认 0 |
| difficulty | string | 筛选难度：Easy/Medium/Hard |
| search | string | 搜索关键词 |

### 响应示例

```json
{
  "problems": [
    {
      "id": "two-sum",
      "title": "两数之和",
      "difficulty": "Easy",
      "description": "给定一个整数数组 nums...",
      "examples": [...]
    }
  ],
  "total": 200
}
```

---

## 6. 用户代码管理

### 保存代码

```
POST /api/v1/user/code
```

### 获取代码

```
GET /api/v1/user/code/{device_id}/{problem_id}
```

### 获取所有代码

```
GET /api/v1/user/code/{device_id}
```

### 获取已通过题目

```
GET /api/v1/user/ac-problems/{device_id}
```

### 保存进度

```
POST /api/v1/user/progress
```

### 获取进度

```
GET /api/v1/user/progress/{device_id}
```

---

## 7. 会话历史管理

### 获取历史

```
GET /api/v1/chat/history/{session_id}
```

### 删除会话

```
DELETE /api/v1/chat/history/{session_id}
```

### 获取会话状态

```
GET /api/v1/chat/session/{session_id}
```

---

## 支持的编程语言

> **注意：当前版本仅支持 Python，更多语言正在开发中**

| 语言 | language 值 | 状态 |
|------|-------------|------|
| Python | `python` | ✅ 支持 |
| JavaScript | `javascript` | ⏳ 计划中 |
| Java | `java` | ⏳ 计划中 |
| C++ | `cpp` | ⏳ 计划中 |
| Go | `go` | ⏳ 计划中 |

---

## 错误类型映射

| Python 异常 | 错误类型 |
|-------------|----------|
| `IndexError` | `IndexError` |
| `KeyError` | `KeyError` |
| `RecursionError` | `RecursionError` |
| `SyntaxError` | `SyntaxError` |
| `IndentationError` | `IndentationError` |
| `TypeError` | `TypeError` |
| `ValueError` | `ValueError` |
| `NameError` | `NameError` |

---

## 常见问题

### Q: 如何使用 DeepSeek-R1 推理模型？

在请求中传入动态配置：

```json
{
  "message": "帮我分析这道题",
  "model_name": "deepseek-reasoner",
  "api_base": "https://api.deepseek.com/v1",
  "api_key": "your-deepseek-api-key"
}
```

### Q: 流式响应如何处理推理过程？

监听 `type: "reasoning"` 事件，模型会在返回内容前先发送思考过程。

### Q: 代码执行超时怎么办？

默认超时为 60 秒。检查代码是否有死循环或无限递归。

### Q: device_id 如何获取？

前端可以使用 `crypto.randomUUID()` 或类似方法生成唯一设备ID，存储在 localStorage 中。

---

## 相关文档

- [SETUP.md](./SETUP.md) - 开发环境搭建
- [USER_GUIDE.md](./USER_GUIDE.md) - 终端用户使用指南
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 系统架构设计
- [API.md](./API.md) - 完整 API 参考
