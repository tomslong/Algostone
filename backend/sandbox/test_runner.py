"""测试用例运行器."""
from typing import List, Dict, Any
import json


class TestRunner:
    """测试用例管理和运行."""
    
    @staticmethod
    def parse_test_cases(test_input: str) -> List[Dict[str, Any]]:
        """
        解析测试用例输入.
        
        Args:
            test_input: 测试用例字符串（如LeetCode格式）
        
        Returns:
            解析后的测试用例列表
        """
        try:
            # 尝试解析JSON格式
            return json.loads(test_input)
        except Exception:
            # 如果不是JSON，按行解析
            test_cases = []
            lines = test_input.strip().split('\n')
            
            for line in lines:
                if line.strip():
                    test_cases.append({'input': line.strip()})
            
            return test_cases
    
    @staticmethod
    def format_test_results(results: List[Dict]) -> str:
        """
        格式化测试结果为可读文本.
        
        Args:
            results: 测试结果列表
        
        Returns:
            格式化的文本
        """
        output = []
        passed_count = sum(1 for r in results if r.get('passed', False))
        total_count = len(results)
        
        output.append(f"测试结果: {passed_count}/{total_count} 通过\n")
        
        for result in results:
            test_num = result.get('test_case', 0)
            passed = result.get('passed', False)
            
            status = "✓ 通过" if passed else "✗ 失败"
            output.append(f"测试用例 {test_num}: {status}")
            
            if not passed:
                if 'error' in result:
                    output.append(f"  错误: {result['error']}")
                elif 'expected' in result and 'actual' in result:
                    output.append(f"  输入: {result.get('input')}")
                    output.append(f"  期望: {result['expected']}")
                    output.append(f"  实际: {result['actual']}")
            
            output.append("")
        
        return "\n".join(output)
    
    @staticmethod
    def analyze_error(error_message: str) -> Dict[str, str]:
        """
        分析错误信息.
        
        Args:
            error_message: 错误消息
        
        Returns:
            错误分析结果
        """
        error_patterns = {
            'IndexError': {
                'type': '数组越界',
                'hint': '检查数组索引是否超出范围。是否在循环中正确使用了索引？'
            },
            'RecursionError': {
                'type': '递归深度超限',
                'hint': '递归调用可能没有正确的终止条件，或者问题规模太大。考虑添加边界条件或使用迭代方式。'
            },
            'KeyError': {
                'type': '字典键不存在',
                'hint': '尝试访问不存在的字典键。使用dict.get()或先检查键是否存在。'
            },
            'AttributeError': {
                'type': '属性不存在',
                'hint': '对象没有该属性或方法。检查对象类型是否正确。'
            },
            'ZeroDivisionError': {
                'type': '除零错误',
                'hint': '尝试除以零。检查分母是否可能为0。'
            },
            'TypeError': {
                'type': '类型错误',
                'hint': '操作或函数应用于不适当类型的对象。检查变量类型是否符合预期。'
            }
        }
        
        for error_type, info in error_patterns.items():
            if error_type in error_message:
                return info
        
        return {
            'type': '运行时错误',
            'hint': '请仔细检查代码逻辑，或查看详细错误信息。'
        }
