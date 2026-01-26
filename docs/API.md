# AlgoStone API 文档

## 基础信息

- **Base URL**: `http://localhost:8001`
- **API 前缀**: `/api/v1`
- **Content-Type**: `application/json`
- **认证**: 设备 ID (device_id)

---

## 题目接口

### 获取题目列表

```http
GET /api/v1/problems
```

**响应示例**:
```json
{
  "problems": [
    {
      "task_id": "two-sum",
      "title": "两数之和",
      "difficulty": "Easy",
      "tags": ["数组", "哈希表"],
      "problem_description": "<p>给定一个整数数组...</p>",
      "starter_code": "class Solution:\n    def solution(self):...",
      "input_output": [
        {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]"}
      ]
    }
  ]
}
```

### 获取题目详情

```http
GET /api/v1/problems/{task_id}
```

---

## 代码执行接口

### 运行代码

```http
POST /api/v1/execute
Content-Type: application/json

{
  "code": "print('hello')",
  "language": "python",
  "test_cases": [
    {"input": "", "expected_output": "hello"}
  ]
}
```

**响应示例**:
```json
{
  "status": "success",
  "output": "hello\n",
  "execution_time": 0.1,
  "error_type": null,
  "error_message": null
}
```

### 提交代码

```http
POST /api/v1/submit
Content-Type: application/json

{
  "device_id": "device-123",
  "problem_id": "two-sum",
  "code": "class Solution:\n...",
  "language": "python",
  "test_results": [
    {"case": 1, "passed": true, "output": "[0,1]"}
  ]
}
```

**响应示例**:
```json
{
  "is_ac": true,
  "message": "提交成功！所有测试通过！"
}
```

---

## AI 对话接口

### 流式对话

```http
POST /api/v1/chat/stream
Content-Type: application/json

{
  "session_id": "device-123",
  "message": "给我一些提示",
  "code": "class Solution:\n...",
  "problem_id": "two-sum",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "api_key": "sk-...",
  "model_name": "gpt-4",
  "api_base": "https://api.openai.com/v1"
}
```

**响应**: Server-Sent Events (SSE) 流式返回

```
data: {"type": "content", "content": "这道题可以..."}
data: {"type": "content", "content": "考虑使用哈希表"}
data: {"type": "end", "full_content": "完整回复"}
```

### 获取聊天历史

```http
GET /api/v1/chat/history/{session_id}
```

**响应示例**:
```json
{
  "messages": [
    {
      "id": 1,
      "session_id": "device-123",
      "task_id": "two-sum",
      "role": "user",
      "content": "给我一些提示",
      "created_at": "2025-01-26T10:00:00Z"
    }
  ]
}
```

### 清空聊天历史

```http
DELETE /api/v1/chat/history/{session_id}
```

---

## 用户数据接口

### 获取已通过题目

```http
GET /api/v1/user/ac-problems/{device_id}
```

**响应示例**:
```json
{
  "ac_problems": ["two-sum", "add-two-numbers"]
}
```

### 保存代码

```http
POST /api/v1/user/code
Content-Type: application/json

{
  "device_id": "device-123",
  "problem_id": "two-sum",
  "code": "class Solution:\n...",
  "language": "python"
}
```

### 获取保存的代码

```http
GET /api/v1/user/code/{device_id}/{problem_id}
```

**响应示例**:
```json
{
  "code": "class Solution:\n...",
  "language": "python",
  "updated_at": "2025-01-26T10:00:00Z"
}
```

---

## 健康检查

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "environment": "development",
  "database": {"status": "healthy"}
}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 422 | 参数验证失败 |
| 429 | 速率限制 |
| 500 | 服务器错误 |

---

## 速率限制

| 端点 | 限制 |
|------|------|
| `/api/v1/chat/*` | 30 次/分钟 |
| `/api/v1/execute` | 60 次/分钟 |
| `/api/v1/submit` | 60 次/分钟 |

响应头包含速率限制信息:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1640000000
```

---

## 交互式文档

开发环境可访问:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
