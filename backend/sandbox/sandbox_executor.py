"""Piston 代码执行器.

使用 Piston API 执行 Python 代码。
"""
import logging
import os
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Optional, List

from app.models.schemas import CodeExecutionResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class SecureCodeExecutor:
    """代码执行器 - 使用 Piston API 执行 Python 代码."""

    PYTHON_VERSION = "3.11.0"

    def __init__(self):
        self.piston_url = os.getenv("PISTON_API_URL", "http://localhost:27123")

    def execute_code(
        self,
        code: str,
        test_cases: Optional[List[Dict]] = None,
        language: str = "python"
    ) -> CodeExecutionResult:
        """执行 Python 代码."""
        # 验证代码长度
        if len(code) > settings.MAX_CODE_LENGTH:
            return CodeExecutionResult(
                status="error",
                error_type="CodeTooLong",
                error_message=f"代码长度超过限制 (最大 {settings.MAX_CODE_LENGTH} 字符)"
            )

        # 只支持 Python
        if language.lower() != "python":
            return CodeExecutionResult(
                status="error",
                error_type="UnsupportedLanguage",
                error_message="暂只支持 Python 语言"
            )

        # 准备输入
        stdin_input = ""
        expected_output = ""
        if test_cases and len(test_cases) > 0:
            stdin_input = test_cases[0].get("input", "")
            expected_output = test_cases[0].get("expected_output", "")

        # 使用 Piston 执行
        return self._execute_with_piston(code, stdin_input, expected_output)

    def _execute_with_piston(
        self,
        code: str,
        stdin_input: str,
        expected_output: str
    ) -> CodeExecutionResult:
        """使用 Piston API 执行代码."""
        url = f"{self.piston_url}/api/v2/execute"

        # Piston API 格式 (timeout 单位是毫秒)
        payload = {
            "language": "python",
            "version": self.PYTHON_VERSION,
            "files": [{"content": code}],
            "stdin": stdin_input,
            "compile_timeout": 10000,  # 10秒 (毫秒)
            "run_timeout": settings.EXECUTION_TIMEOUT_SECONDS * 1000,  # 转换为毫秒
        }

        logger.info(f"Piston request: {url}, Code length: {len(code)}, run_timeout: {payload['run_timeout']}")

        try:
            # 使用 urllib.request 发送请求
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                }
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)

            # 解析响应 (Piston v2 格式)
            run = data.get("run", {})
            stdout = run.get("stdout", "") or ""
            stderr = run.get("stderr", "") or ""
            exit_code = run.get("code", 0)  # Piston v2 使用 code 而不是 exitCode
            signal = run.get("signal")
            cpu_time_ms = run.get("cpu_time", 0)  # 毫秒
            memory = run.get("memory", 0)

            logger.info(f"Piston response: code={exit_code}, signal={signal}")

            # 运行时错误
            if stderr:
                error_type = self._parse_error_type(stderr)
                return CodeExecutionResult(
                    status="error",
                    error_type=error_type,
                    error_message=stderr,
                )

            # 信号导致的错误 (如超时、内存超限)
            if signal:
                if signal == "SIGXCPU":
                    return CodeExecutionResult(
                        status="error",
                        error_type="TimeoutError",
                        error_message=f"执行超时 ({settings.EXECUTION_TIMEOUT_SECONDS}秒)",
                    )
                if signal in ["SIGSEGV", "SIGABRT"]:
                    return CodeExecutionResult(
                        status="error",
                        error_type="RuntimeError",
                        error_message=f"程序崩溃 ({signal})",
                    )
                return CodeExecutionResult(
                    status="error",
                    error_type="RuntimeError",
                    error_message=f"执行错误: {signal}",
                )

            # 退出码非零
            if exit_code != 0:
                return CodeExecutionResult(
                    status="error",
                    error_type="RuntimeError",
                    error_message=f"程序异常退出 (exit code: {exit_code})",
                )

            # 成功 - 检查输出
            if expected_output:
                actual = self._normalize_output(stdout)
                expected = self._normalize_output(expected_output)
                if actual != expected:
                    return CodeExecutionResult(
                        status="error",
                        error_type="WrongAnswer",
                        error_message=f"期望输出: {expected_output}\n实际输出: {stdout}",
                    )

            return CodeExecutionResult(
                status="success",
                output=stdout,
                execution_time=cpu_time_ms / 1000,  # 转换为秒
                memory_usage=memory,
            )

        except urllib.error.HTTPError as e:
            # 打印详细的错误响应
            error_body = e.read().decode('utf-8') if e.fp else ""
            logger.error(f"Piston HTTP Error: {e.code}")
            logger.error(f"Response text: {error_body[:500]}")
            return CodeExecutionResult(
                status="error",
                error_type="SystemError",
                error_message=f"Piston 服务错误: {e.code}",
            )
        except urllib.error.URLError as e:
            logger.error(f"Piston connection error: {e.reason}")
            return CodeExecutionResult(
                status="error",
                error_type="SystemError",
                error_message=f"无法连接到 Piston 服务 ({self.piston_url})，请确保服务已启动",
            )
        except Exception as e:
            logger.error(f"Piston 执行错误: {e}")
            return CodeExecutionResult(
                status="error",
                error_type="SystemError",
                error_message=f"执行失败: {str(e)}",
            )

    def _normalize_output(self, value: str) -> str:
        """标准化输出 (去除多余空白)."""
        return re.sub(r"\s+", "", str(value).strip())

    def _parse_error_type(self, error_message: str) -> str:
        """解析错误类型."""
        error_patterns = {
            "SyntaxError": "SyntaxError",
            "IndexError": "IndexError",
            "KeyError": "KeyError",
            "NameError": "NameError",
            "TypeError": "TypeError",
            "ValueError": "ValueError",
            "AttributeError": "AttributeError",
            "ZeroDivisionError": "ZeroDivisionError",
            "ImportError": "ImportError",
            "ModuleNotFoundError": "ImportError",
            "IndentationError": "SyntaxError",
            "TabError": "SyntaxError",
        }

        for error_name, error_type in error_patterns.items():
            if error_name in error_message:
                return error_type

        return "RuntimeError"


# 全局实例
executor = SecureCodeExecutor()
