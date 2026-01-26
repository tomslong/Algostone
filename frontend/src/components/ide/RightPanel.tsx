import React, { useState, memo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Play, Send, RotateCcw, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import axios from 'axios';
import { toast } from 'sonner';
import { LeetCodeProblem } from '@/contexts/ProblemContext';
import { getCurrentCode } from './Workspace';
import { API_ENDPOINTS } from '@/config';
import { cn } from '@/lib/utils';
import { getDeviceId } from '@/lib/device';

interface RightPanelProps {
  currentProblem?: LeetCodeProblem | null;
}

interface TestCase {
  input: string;
  output: string;
}

interface TestResult {
  case: number;
  passed: boolean;
  status: string;
  output: string;
  time: number;
}

export const RightPanel = memo(({ currentProblem }: RightPanelProps) => {
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[] | null>(null);
  const [expandedCases, setExpandedCases] = useState<Record<number, boolean>>({});

  const handleRunCode = async () => {
    setIsRunning(true);
    setTestResults(null);

    let testCode = '';

    try {
      const code = getCurrentCode();
      const testCases = currentProblem?.input_output || [];

      if (!currentProblem || testCases.length === 0) {
        toast.error('没有可用的测试用例');
        setIsRunning(false);
        return;
      }

      if (!code || code.trim() === '') {
        toast.error('请先编写代码');
        setIsRunning(false);
        return;
      }

      // 获取函数签名
      const getFunctionSignature = (starterCode: string) => {
        const match = starterCode.match(/def\s+(\w+)\s*\((.*?)\)/);
        if (match) {
          return { name: match[1], params: match[2] };
        }
        return { name: 'solution', params: 'self' };
      };

      const funcSig = getFunctionSignature(currentProblem.starter_code);

      // 常用 Python 导入（LeetCode 题目常用）
      const commonImports = `from typing import List, Optional, Dict, Tuple, Set
import collections
import itertools
import math
import re
from functools import lru_cache
from heapq import heappush, heappop, heapify
from bisect import bisect_left, bisect_right
`;

      // 构造完整代码（包含导入、Solution 类和测试）
      testCode = `
${commonImports}

${code}

def _normalize(value):
    import re
    return re.sub(r"\\s+", "", str(value))

sol = Solution()
results = []
`;

      // 添加测试用例执行
      testCases.forEach((tc: TestCase, tcIndex: number) => {
        const caseNum = tcIndex + 1;
        testCode += `
try:
    result = sol.${funcSig.name}(${tc.input})
    expected = ${JSON.stringify(tc.output)}
    if _normalize(str(result)) == _normalize(str(expected)):
        print(f"TEST_CASE_${caseNum}:PASSED:{result}")
        results.append(True)
    else:
        print(f"TEST_CASE_${caseNum}:FAILED:Expected {expected}, got {result}")
        results.append(False)
except Exception as e:
    print(f"TEST_CASE_${caseNum}:ERROR:{str(e)}")
    results.append(False)
`;
      });

      testCode += `
print(f"SUMMARY:{len([r for r in results if r])}/{len(results)}")
`;

      const response = await axios.post(API_ENDPOINTS.EXECUTE, {
        code: testCode,  // 发送完整的测试代码（包含测试用例）
        language: 'python',
      });

      // 解析输出
      const output = response.data.output || response.data.stdout || '';
      const parsedResults = parseTestOutput(output);
      setTestResults(parsedResults);

      if (parsedResults.length === 0) {
        // 没有解析到测试结果，可能是输出格式不对
        toast.error('测试执行出错：无法解析结果');
      } else {
        const allPassed = parsedResults.every(r => r.passed);
        if (allPassed) {
          toast.success('所有测试用例通过！');
        } else if (parsedResults.some(r => r.passed)) {
          toast.error(`部分测试用例未通过 (${parsedResults.filter(r => r.passed).length}/${parsedResults.length})`);
        }
      }

    } catch (error: any) {
      // 显示详细错误信息
      const details = error.response?.data?.details;
      if (details && details.length > 0) {
        const firstError = details[0];
        const loc = firstError?.loc ? `(${firstError.loc.join('.')}) ` : '';
        toast.error(`验证失败 ${loc}: ${firstError.msg}`);
      } else {
        toast.error('请求失败: ' + (error.response?.data?.message || error.message));
      }
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmitCode = async () => {
    setIsSubmitting(true);

    try {
      const code = getCurrentCode();
      const testCases = currentProblem?.input_output || [];

      if (!currentProblem || testCases.length === 0) {
        toast.error('没有可用的测试用例');
        setIsSubmitting(false);
        return;
      }

      if (!code || code.trim() === '') {
        toast.error('请先编写代码');
        setIsSubmitting(false);
        return;
      }

      // 先运行测试获取结果
      const runResults = await runTestsAndGetResults(code, testCases, currentProblem.starter_code);

      // 检查是否全部通过
      const allPassed = runResults.every(r => r.passed);

      if (!allPassed) {
        toast.error(`有测试用例未通过 (${runResults.filter(r => r.passed).length}/${runResults.length})`);
        setTestResults(runResults);
        setIsSubmitting(false);
        return;
      }

      // 全部通过，提交到后端
      const deviceId = getDeviceId();
      const response = await axios.post(API_ENDPOINTS.SUBMIT, {
        device_id: deviceId,
        problem_id: currentProblem.task_id,
        code: code,
        language: 'python',
        test_results: runResults,
      });

      if (response.data.is_ac) {
        toast.success('🎉 提交成功！所有测试通过！');
        // 刷新 AC 状态
        window.location.reload();
      } else {
        toast.error('提交失败，请重试');
      }

    } catch (error: any) {
      console.error('Submit failed:', error);
      toast.error('提交失败: ' + (error.response?.data?.message || error.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  const runTestsAndGetResults = async (code: string, testCases: TestCase[], starterCode: string): Promise<TestResult[]> => {
    // 获取函数签名
    const getFunctionSignature = (starterCode: string) => {
      const match = starterCode.match(/def\s+(\w+)\s*\((.*?)\)/);
      if (match) {
        return { name: match[1], params: match[2] };
      }
      return { name: 'solution', params: 'self' };
    };

    const funcSig = getFunctionSignature(starterCode);

    // 常用 Python 导入
    const commonImports = `from typing import List, Optional, Dict, Tuple, Set
import collections
import itertools
import math
import re
from functools import lru_cache
from heapq import heappush, heappop, heapify
from bisect import bisect_left, bisect_right
`;

    // 构造测试代码
    let testCode = `
${commonImports}

${code}

def _normalize(value):
    import re
    return re.sub(r"\\s+", "", str(value))

sol = Solution()
results = []
`;

    testCases.forEach((tc: TestCase, tcIndex: number) => {
      const caseNum = tcIndex + 1;
      testCode += `
try:
    result = sol.${funcSig.name}(${tc.input})
    expected = ${JSON.stringify(tc.output)}
    if _normalize(str(result)) == _normalize(str(expected)):
        print(f"TEST_CASE_${caseNum}:PASSED:{result}")
        results.append(True)
    else:
        print(f"TEST_CASE_${caseNum}:FAILED:Expected {expected}, got {result}")
        results.append(False)
except Exception as e:
    print(f"TEST_CASE_${caseNum}:ERROR:{str(e)}")
    results.append(False)
`;
    });

    testCode += `
print(f"SUMMARY:{len([r for r in results if r])}/{len(results)}")
`;

    // 执行
    const response = await axios.post(API_ENDPOINTS.EXECUTE, {
      code: testCode,
      language: 'python',
    });

    const output = response.data.output || response.data.stdout || '';
    return parseTestOutput(output);
  };

  const parseTestOutput = (output: string): TestResult[] => {
    const results: TestResult[] = [];
    const lines = output.split('\n');

    for (const line of lines) {
      if (line.startsWith('TEST_CASE_')) {
        const parts = line.split(':');
        if (parts.length >= 3) {
          const caseNum = parseInt(parts[0].replace('TEST_CASE_', ''));
          const status = parts[1];
          const message = parts.slice(2).join(':');

          results.push({
            case: caseNum,
            passed: status === 'PASSED',
            status: status === 'PASSED' ? 'Passed' : status === 'ERROR' ? 'Error' : 'Failed',
            output: message,
            time: 0,
          });
        }
      }
    }

    return results;
  };

  const toggleCase = (caseNum: number) => {
    setExpandedCases(prev => ({ ...prev, [caseNum]: !prev[caseNum] }));
  };

  const testCases = currentProblem?.input_output || [];
  const passedCount = testResults?.filter(r => r.passed).length || 0;
  const totalCount = testResults?.length || testCases.length || 0;

  return (
    <div className="h-full w-full flex flex-col border-l bg-card overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="border-b px-4 py-3 bg-background/50 shrink-0">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Test Result</h3>
              {testResults ? (
                <Badge variant={passedCount === totalCount ? "default" : "secondary"} className="text-xs">
                  {passedCount}/{totalCount} passed
                </Badge>
              ) : currentProblem?.input_output && currentProblem.input_output.length > 0 ? (
                <Badge variant="secondary" className="text-xs">
                  {currentProblem.input_output.length} cases
                </Badge>
              ) : null}
            </div>
          </div>

          {/* Result Content */}
          <ScrollArea className="flex-1 px-3">
            {isRunning ? (
              <div className="flex flex-col items-center justify-center h-full py-10 text-muted-foreground gap-2">
                <Loader2 className="h-8 w-8 animate-spin" />
                <div className="text-sm">Running tests...</div>
              </div>
            ) : testResults ? (
              <div className="py-3 space-y-2">
                {testResults.map((result) => (
                  <Collapsible
                    key={result.case}
                    open={expandedCases[result.case] || !result.passed}
                    onOpenChange={() => toggleCase(result.case)}
                  >
                    <CollapsibleTrigger asChild>
                      <div
                        className={cn(
                          "flex items-center gap-2 p-3 rounded-lg border cursor-pointer hover:bg-accent/50 transition-colors",
                          result.passed
                            ? "bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800"
                            : "bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800"
                        )}
                      >
                        {result.passed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
                        )}
                        <div className="flex-1 text-left">
                          <div className="text-sm font-medium">
                            Case {result.case}: {result.status}
                          </div>
                          {testCases[result.case - 1] && (
                            <div className="text-xs text-muted-foreground mt-0.5 truncate">
                              Input: {testCases[result.case - 1].input}
                            </div>
                          )}
                        </div>
                        {expandedCases[result.case] ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                        )}
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="px-3 pb-2">
                        {testCases[result.case - 1] && (
                          <div className="text-xs space-y-2 mt-2">
                            <div>
                              <span className="text-muted-foreground">Input:</span>
                              <code className="ml-2 bg-muted px-2 py-1 rounded block mt-1 break-all">
                                {testCases[result.case - 1].input}
                              </code>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Expected:</span>
                              <code className="ml-2 bg-muted px-2 py-1 rounded block mt-1 break-all">
                                {testCases[result.case - 1].output}
                              </code>
                            </div>
                            {!result.passed && (
                              <div>
                                <span className={result.status === 'Error' ? "text-red-500" : "text-orange-500"}>
                                  {result.status === 'Error' ? 'Error:' : 'Your Output:'}
                                </span>
                                <code className="ml-2 bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded block mt-1 break-all text-red-600 dark:text-red-400">
                                  {result.output}
                                </code>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full py-10 text-muted-foreground gap-2">
                <Play className="h-8 w-8 opacity-20" />
                <div className="text-sm">Run code to see results</div>
                {currentProblem?.input_output && currentProblem.input_output.length > 0 && (
                  <div className="text-xs opacity-50">{currentProblem.input_output.length} test cases available</div>
                )}
              </div>
            )}
          </ScrollArea>
        </div>
      </div>

      <div className="p-3 border-t bg-background shrink-0">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 h-9"
            onClick={() => {
              setTestResults(null);
              toast.info('已重置');
            }}
          >
            <RotateCcw className="mr-1 h-3 w-3" /> Reset
          </Button>
          <Button
            variant="secondary"
            size="sm"
            className="flex-1 h-9"
            onClick={handleRunCode}
            disabled={isRunning}
          >
            {isRunning ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Play className="mr-1 h-3 w-3" />}
            Run
          </Button>
          <Button
            size="sm"
            className="flex-1 h-9 bg-green-600 hover:bg-green-700 text-white"
            onClick={handleSubmitCode}
            disabled={isSubmitting}
          >
            {isSubmitting ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <Send className="mr-1 h-3 w-3" />}
            Submit
          </Button>
        </div>
      </div>
    </div>
  );
});

