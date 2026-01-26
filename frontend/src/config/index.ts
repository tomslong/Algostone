/**
 * 全局配置文件
 * 统一管理环境变量和常量
 */

// ============================================================================
// API 配置
// ============================================================================

// API 基础地址
export const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8001';

// API 完整地址
export const API_URL = `${API_BASE_URL}/api/v1`;

// API 端点
export const API_ENDPOINTS = {
  // 问题相关
  PROBLEMS: `${API_URL}/problems`,
  PROBLEM_BY_ID: (id: string) => `${API_URL}/problems/${id}`,

  // 聊天相关
  CHAT_SEND: `${API_URL}/chat/send`,
  CHAT_STREAM: `${API_URL}/chat/stream`,
  CHAT_HISTORY: (sessionId: string, taskId?: string | null) =>
    taskId ? `${API_URL}/chat/history/${sessionId}?task_id=${taskId}` : `${API_URL}/chat/history/${sessionId}`,

  // 执行相关
  EXECUTE: `${API_URL}/execute`,

  // 设置相关
  TEST_CONNECTION: `${API_URL}/settings/test-connection`,

  // 认证相关
  AUTH_LOGIN: `${API_URL}/auth/login`,
  AUTH_REGISTER: `${API_URL}/auth/register`,
  AUTH_VERIFY: `${API_URL}/auth/verify`,
  AUTH_REFRESH: `${API_URL}/auth/refresh`,

  // 用户进度相关
  USER_PROGRESS: `${API_URL}/user/progress`,
  USER_SUBMISSIONS: `${API_URL}/user/submissions`,
  SAVE_CODE: `${API_URL}/user/code`,
  SUBMIT: `${API_URL}/user/submit`,
  AC_PROBLEMS: (deviceId: string) => `${API_URL}/user/ac-problems/${deviceId}`,
} as const;

// 超时配置
export const API_TIMEOUT = 60000; // 60秒

// WebSocket 地址 (如果需要)
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE || API_BASE_URL.replace('http', 'ws');

// ============================================================================
// LocalStorage 键名 (仅用于临时/客户端配置)
// ============================================================================

export const STORAGE_KEYS = {
  // API 设置 (客户端配置)
  API_SETTINGS: 'algostone_api_settings',

  // 认证 Token (客户端缓存)
  AUTH_TOKEN: 'auth_token',

  // 主题 (客户端配置)
  THEME: 'vite-ui-theme',

  // 临时会话 ID (用于匿名用户聊天)
  SESSION_ID: 'algostone_session_id',
} as const;

// ============================================================================
// 默认配置值
// ============================================================================

export const DEFAULT_SETTINGS = {
  // API 默认值
  API_KEY: '',
  MODEL_NAME: 'qwen-plus',
  API_BASE: 'https://dashscope.aliyuncs.com/compatible-mode/v1',

  // 问题默认值
  PROBLEM_LIMIT: 500,

  // 主题默认值
  THEME: 'dark',
} as const;

// ============================================================================
// 应用配置
// ============================================================================

export const APP_CONFIG = {
  name: 'AlgoStone',
  version: '1.0.0',
  description: 'AI驱动的算法学习平台',
} as const;

// ============================================================================
// 意图类型 (与后端保持一致)
// ============================================================================

export const INTENT_TYPES = {
  SUBMIT_CODE: 'submit_code',
  ASK_CONCEPT: 'ask_concept',
  REQUEST_HINT: 'request_hint',
  OTHER: 'other',
} as const;

// ============================================================================
// 代码语言配置
// ============================================================================

export const LANGUAGES = {
  PYTHON: 'python',
  JAVASCRIPT: 'javascript',
  JAVA: 'java',
  CPP: 'cpp',
  GO: 'go',
  RUST: 'rust',
} as const;

// ============================================================================
// 难度级别
// ============================================================================

export const DIFFICULTY_LEVELS = {
  EASY: 'Easy',
  MEDIUM: 'Medium',
  HARD: 'Hard',
} as const;
