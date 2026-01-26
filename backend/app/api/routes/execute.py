"""代码执行路由 - 安全增强版.

特性:
- 速率限制
- 输入验证
- 使用安全沙箱执行器
- 错误消息脱敏
"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.schemas import CodeExecutionRequest, CodeExecutionResult
from sandbox.sandbox_executor import executor
from app.core.config import settings
from app.core.security import sanitize_for_log

router = APIRouter()
logger = logging.getLogger(__name__)

# 速率限制器
limiter = Limiter(key_func=get_remote_address)


@router.get("/test-piston")
async def test_piston():
    """测试 Piston 连接."""
    try:
        import httpx
        response = await httpx.post(
            "http://localhost:27123/api/v2/execute",
            json={"language": "python", "version": "3.11.0", "files": [{"content": "print('Piston OK')"}]},
            timeout=10
        )
        return {"status": "ok", "response": response.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/execute", response_model=CodeExecutionResult)
@limiter.limit(f"{settings.RATE_LIMIT_EXECUTE_PER_MINUTE}/minute")
async def execute_code(request: Request, req: CodeExecutionRequest):
    """
    执行代码 (单次).

    速率限制: 每分钟 {settings.RATE_LIMIT_EXECUTE_PER_MINUTE} 次
    """
    # 额外验证 (Pydantic 已处理)
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="代码不能为空")

    logger.info(f"代码执行请求: language={req.language}, code_length={len(req.code)}")

    try:
        result = executor.execute_code(
            code=req.code,
            test_cases=req.test_cases,
            language=req.language.lower(),
        )
        # 记录结果
        logger.info(f"执行结果: status={result.status}, error_type={result.error_type}")
        if result.status == "error":
            logger.error(f"执行错误详情: {result.error_message[:200]}")
        return result

    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        return CodeExecutionResult(
            status="error",
            error_type="SystemError",
            error_message="代码执行服务暂时不可用",
        )


@router.post("/submit", response_model=CodeExecutionResult)
@limiter.limit(f"{settings.RATE_LIMIT_EXECUTE_PER_MINUTE}/minute")
async def submit_code(request: Request, req: CodeExecutionRequest):
    """
    提交代码 - 运行所有测试用例.

    速率限制: 每分钟 {settings.RATE_LIMIT_EXECUTE_PER_MINUTE} 次
    """
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="代码不能为空")

    if not req.test_cases or len(req.test_cases) == 0:
        return await execute_code(request, req)

    logger.info(f"代码提交: language={req.language}, test_cases={len(req.test_cases)}")

    test_results: List[Dict[str, Any]] = []
    total_time = 0.0

    for i, test_case in enumerate(req.test_cases):
        expected_output = test_case.get("expected_output") or test_case.get("output", "")
        single_test_case = [{"input": test_case.get("input", ""), "expected_output": expected_output}]

        try:
            result = executor.execute_code(
                code=req.code,
                test_cases=single_test_case,
                language=req.language.lower(),
            )

            passed = result.status == "success"
            time_taken = result.execution_time or 0.0

            test_results.append({
                "case": i + 1,
                "passed": passed,
                "status": "Passed" if passed else "Failed",
                "output": result.output or result.error_message or "",
                "time": time_taken,
            })

            total_time += time_taken

        except Exception as e:
            logger.error(f"Test case {i+1} error: {e}")
            test_results.append({
                "case": i + 1,
                "passed": False,
                "status": "Error",
                "output": "测试执行出错",
                "time": 0,
            })

    passed_count = sum(1 for r in test_results if r["passed"])
    total_count = len(test_results)

    output_lines = []
    for r in test_results:
        status_symbol = "✓" if r["passed"] else "✗"
        output_lines.append(f"Case {r['case']}: {status_symbol} {r['status']}")
        if r["output"] and r["output"] != "Error":
            output_lines.append(f"  Output: {r['output'][:100]}")

    output_lines.append(f"\n{passed_count}/{total_count} test cases passed")
    if passed_count == total_count:
        output_lines.append("\n🎉 All tests passed!")
    else:
        output_lines.append(f"\n❌ {total_count - passed_count} test cases failed")

    return CodeExecutionResult(
        status="success" if passed_count == total_count else "error",
        error_type=None if passed_count == total_count else "WrongAnswer",
        output="\n".join(output_lines),
        execution_time=total_time,
    )
