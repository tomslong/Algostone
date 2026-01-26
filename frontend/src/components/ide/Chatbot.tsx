import React, { useState, useRef, useEffect, useCallback, memo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Bot, User, Send, Sparkles, Loader2, Trash2, StopCircle, ChevronDown, ChevronRight, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { loadSettings } from '@/lib/settings';
import { getDeviceId } from '@/lib/device';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_ENDPOINTS } from '@/config';
import { getCurrentCode } from './Workspace';

interface Message {
  id: number;
  session_id: string;
  task_id: string | null;
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string;  // 推理过程 (DeepSeek-R1 等模型)
  created_at: string;
}

interface ChatbotProps {
  currentProblemId?: string | null;
}

export const Chatbot = memo(({ currentProblemId }: ChatbotProps) => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  // 使用 device_id 作为全局聊天 ID，跨题目共享对话历史
  const sessionId = getDeviceId();
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // 追踪哪些消息的推理过程是展开的
  const [expandedReasoning, setExpandedReasoning] = useState<Set<number>>(new Set());

  // 加载全局聊天历史（不按 task_id 过滤）
  useEffect(() => {
    loadChatHistory();
  }, [currentProblemId]); // currentProblemId 变化时重新加载（可能需要显示当前题目的相关信息）

  const loadChatHistory = async () => {
    try {
      // 只按 session_id 获取，不按 task_id 过滤
      const url = API_ENDPOINTS.CHAT_HISTORY(sessionId);

      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        if (data.messages) {
          setMessages(data.messages);
        }
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  // 停止生成
  const handleStop = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setIsLoading(false);
    }
  }, [abortController]);

  // 切换推理过程展开/折叠
  const toggleReasoning = useCallback((msgId: number) => {
    setExpandedReasoning(prev => {
      const newSet = new Set(prev);
      if (newSet.has(msgId)) {
        newSet.delete(msgId);
      } else {
        newSet.add(msgId);
      }
      return newSet;
    });
  }, []);

  // 发送消息（流式）
  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // 添加用户消息
    const userMsg: Message = {
      id: Date.now(),
      session_id: sessionId,
      task_id: currentProblemId || null,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    scrollToBottom();

    const settings = loadSettings();
    if (!settings.openai_api_key || !settings.model_name || !settings.api_base) {
      toast.error('请先在设置页面配置 API 信息');
      setIsLoading(false);
      const errorMsg: Message = {
        id: Date.now() + 1,
        session_id: sessionId,
        task_id: currentProblemId || null,
        role: 'assistant',
        content: '请先在设置页面配置 API 信息。',
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
      return;
    }

    // 创建 AbortController 用于取消请求
    const controller = new AbortController();
    setAbortController(controller);

    // 创建一个空的助手消息，用于流式更新
    const assistantMsgId = Date.now() + 2;
    const assistantMsg: Message = {
      id: assistantMsgId,
      session_id: sessionId,
      task_id: currentProblemId || null,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      const currentCode = getCurrentCode();

      const response = await fetch(API_ENDPOINTS.CHAT_STREAM, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage,
          code: currentCode,
          problem_id: currentProblemId,
          conversation_history: messages.filter(m => m.id !== userMsg.id && m.id !== assistantMsg.id)
            .map(m => ({ role: m.role, content: m.content })),
          api_key: settings.openai_api_key,
          model_name: settings.model_name,
          api_base: settings.api_base
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // 处理流式响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'content') {
                  // 更新消息内容
                  fullContent += data.content;
                  setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, content: fullContent }
                      : msg
                  ));
                  scrollToBottom();
                } else if (data.type === 'reasoning') {
                  // 推理过程 (DeepSeek-R1 等模型)
                  setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, reasoning: data.content }
                      : msg
                  ));
                  scrollToBottom();
                } else if (data.type === 'error') {
                  toast.error('AI 响应出错: ' + data.message);
                  setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, content: `错误: ${data.message}` }
                      : msg
                  ));
                } else if (data.type === 'end') {
                  // 流结束
                  setMessages(prev => prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, content: fullContent || msg.content }
                      : msg
                  ));
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e);
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        toast.info('已停止生成');
      } else {
        console.error('Chatbot error:', error);
        toast.error('发送失败: ' + (error.message || '未知错误'));

        setMessages(prev => prev.map(msg =>
          msg.id === assistantMsgId && msg.role === 'assistant' && msg.content === ''
            ? { ...msg, content: `错误: ${error.message}` }
            : msg
        ));
      }
    } finally {
      setAbortController(null);
      setIsLoading(false);
    }
  };

  const handleClearMessages = async () => {
    try {
      // 清空全局聊天历史（不按 task_id 过滤）
      const url = API_ENDPOINTS.CHAT_HISTORY(sessionId);
      await fetch(url, { method: 'DELETE' });
      setMessages([]);
      toast.info('对话已清空');
    } catch (error) {
      console.error('Failed to clear messages:', error);
      toast.error('清空失败');
    }
  };

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollArea = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollArea) {
        scrollArea.scrollTop = scrollArea.scrollHeight;
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading) {
        handleSendMessage();
      }
    }
  };

  // 快捷操作按钮
  const quickActions = [
    { icon: Sparkles, color: 'text-yellow-500', label: '给我一些提示', prompt: '给我一些提示' },
    { icon: Sparkles, color: 'text-blue-500', label: '帮我优化代码', prompt: '帮我优化代码' },
    { icon: Sparkles, color: 'text-green-500', label: '解释这个算法', prompt: '解释这个算法' },
  ];

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="px-3 py-2 border-b flex items-center justify-between bg-muted/20">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">Algorithm Bot</h3>
            <p className="text-xs text-muted-foreground">Powered by LangGraph</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClearMessages}
          className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
          title="清空对话"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 w-full px-3" ref={scrollAreaRef}>
        <div className="py-3 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-10 text-muted-foreground gap-3">
              <Bot className="h-12 w-12 opacity-20" />
              <div className="text-sm">开始提问关于算法的问题</div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "flex gap-3 max-w-[85%]",
                  msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'flex-row'
                )}
              >
                <div
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0",
                    msg.role === 'user' ? 'bg-primary' : 'bg-muted'
                  )}
                >
                  {msg.role === 'user' ? (
                    <User className="h-4 w-4 text-primary-foreground" />
                  ) : (
                    <Bot className="h-4 w-4 text-foreground" />
                  )}
                </div>
                <div
                  className={cn(
                    "rounded-lg px-4 py-2 text-sm max-w-full",
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-foreground'
                  )}
                >
                  {msg.role === 'assistant' ? (
                    <>
                      {/* 推理过程 (可折叠) */}
                      {msg.reasoning && (
                        <div className="mb-3 border-b border-border pb-3">
                          <button
                            onClick={() => toggleReasoning(msg.id)}
                            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors w-full text-left"
                          >
                            {expandedReasoning.has(msg.id) ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            <Brain className="h-3.5 w-3.5" />
                            <span>思考过程</span>
                          </button>
                          {expandedReasoning.has(msg.id) && (
                            <div className="mt-2 text-xs text-muted-foreground bg-muted-foreground/10 rounded p-2 whitespace-pre-wrap">
                              {msg.reasoning}
                            </div>
                          )}
                        </div>
                      )}
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({node, ...props}) => <h1 className="text-lg font-bold mt-3 mb-2" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-base font-semibold mt-2 mb-1" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-sm font-semibold mt-1 mb-1" {...props} />,
                          p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 ml-4 space-y-1" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 ml-4 space-y-1" {...props} />,
                          li: ({node, ...props}) => <li className="text-sm" {...props} />,
                          code: ({node, inline, className, children, ...props}) => {
                            const isInline = inline || !className?.includes('language-');
                            return (
                              <code
                                className={cn(
                                  "rounded text-xs font-mono",
                                  isInline
                                    ? "bg-muted px-1.5 py-0.5 text-foreground"
                                    : "block bg-muted-foreground/50 px-3 py-2 my-2 text-foreground whitespace-pre-wrap break-words"
                                )}
                                {...props}
                              >
                                {children}
                              </code>
                            );
                          },
                          pre: ({node, children, ...props}) => (
                            <pre
                              className="bg-muted/50 rounded-lg p-3 overflow-x-auto my-2 text-xs whitespace-pre-wrap"
                              {...props}
                            >
                              {children}
                            </pre>
                          ),
                          strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                          a: ({node, ...props}) => (
                            <a className="text-primary hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />

          {/* 正在输入指示器 */}
          {isLoading && messages.some(m => m.role === 'assistant' && m.content === '') && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                <Bot className="h-4 w-4 animate-pulse text-muted-foreground" />
              </div>
              <div className="rounded-lg px-4 py-2 bg-muted text-foreground text-sm">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  AI 正在思考...
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="w-full p-3 border-t bg-muted/20">
        <div className="flex gap-2 w-full">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="问我关于算法的问题..."
            className="flex-1"
            disabled={isLoading}
          />
          {isLoading ? (
            <Button
              size="icon"
              variant="destructive"
              onClick={handleStop}
              title="停止生成"
            >
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSendMessage}
              disabled={!inputValue.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Quick Actions */}
        {messages.length === 0 && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {quickActions.map((action) => (
              <Button
                key={action.label}
                variant="outline"
                size="sm"
                className="text-xs h-7 whitespace-nowrap"
                onClick={() => setInputValue(action.prompt)}
                disabled={isLoading}
              >
                <action.icon className="mr-1 h-3 w-3" />
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});
