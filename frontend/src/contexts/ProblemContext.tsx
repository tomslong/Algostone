import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { API_ENDPOINTS, DEFAULT_SETTINGS } from '@/config';
import { saveProgress, getProgress } from '@/lib/userApi';

export interface LeetCodeProblem {
  task_id: string;
  question_id: number;
  title: string;  // 从 task_id 衍生
  difficulty: string;
  tags: string[];
  problem_description: string;
  starter_code: string;
  estimated_date?: string;
  prompt?: string;
  completion?: string;
  entry_point?: string;
  test?: string;
  input_output: Array<{input: string; output: string}>;
  query?: string;
  response?: string;
}

interface ProblemContextType {
  problems: LeetCodeProblem[];
  currentProblem: LeetCodeProblem | null;
  loading: boolean;
  error: string | null;
  selectProblem: (problemId: string) => void;
  refreshProblems: () => void;
}

const ProblemContext = createContext<ProblemContextType | undefined>(undefined);

const DEFAULT_PROBLEM_LIMIT = DEFAULT_SETTINGS.PROBLEM_LIMIT;

export function ProblemProvider({ children }: { children: ReactNode }) {
  const [problems, setProblems] = useState<LeetCodeProblem[]>([]);
  const [currentProblem, setCurrentProblem] = useState<LeetCodeProblem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // 加载题目列表
  const fetchProblems = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(API_ENDPOINTS.PROBLEMS + `?limit=${DEFAULT_PROBLEM_LIMIT}`);
      // API 返回格式: {total: number, problems: [...]}
      const problemsData = response.data.problems || [];

      // 添加 title 字段（从 task_id 衍生）
      const problemsWithTitle = problemsData.map((p: any) => ({
        ...p,
        title: p.task_id.split('-').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
      }));

      setProblems(problemsWithTitle);

      // 默认选择第一题
      if (problemsWithTitle.length > 0 && !currentProblem) {
        setCurrentProblem(problemsWithTitle[0]);
      }
    } catch (err) {
      console.error('Failed to fetch problems:', err);
      setError('加载题目失败');
    } finally {
      setLoading(false);
    }
  };

  // 选择题目
  const selectProblem = async (problemId: string) => {
    // 先从本地列表中查找
    const problem = problems.find(p => p.task_id === problemId || p.title === problemId);
    if (problem) {
      setCurrentProblem(problem);
      // 保存进度到数据库
      await saveProgress(problemId);
    } else {
      // 如果本地没有，从 API 获取详情
      try {
        const response = await axios.get(API_ENDPOINTS.PROBLEM_BY_ID(problemId));
        const problemData = response.data;
        // 添加 title 字段
        problemData.title = problemData.task_id.split('-').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        setCurrentProblem(problemData);
        await saveProgress(problemId);
      } catch (err) {
        console.error('Failed to fetch problem detail:', err);
      }
    }
  };

  // 刷新题目列表
  const refreshProblems = () => {
    fetchProblems();
  };

  // 初始化：加载题目列表
  useEffect(() => {
    fetchProblems();
  }, []);

  // 恢复上次选择的题目（从数据库）
  useEffect(() => {
    const restoreProgress = async () => {
      if (isInitialized || problems.length === 0) return;

      const progress = await getProgress();
      if (progress?.current_problem_id) {
        const problem = problems.find(p =>
          p.task_id === progress.current_problem_id ||
          p.title === progress.current_problem_id
        );
        if (problem) {
          setCurrentProblem(problem);
        }
      }
      setIsInitialized(true);
    };

    restoreProgress();
  }, [problems, isInitialized]);

  return (
    <ProblemContext.Provider
      value={{
        problems,
        currentProblem,
        loading,
        error,
        selectProblem,
        refreshProblems,
      }}
    >
      {children}
    </ProblemContext.Provider>
  );
}

export function useProblem() {
  const context = useContext(ProblemContext);
  if (!context) {
    throw new Error('useProblem must be used within a ProblemProvider');
  }
  return context;
}
