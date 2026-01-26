import React, { useEffect, useRef, useState, lazy, Suspense, memo } from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from '@/components/ui/badge';
import { BookOpen, Code2, Bot, Loader2, Sun, Moon } from 'lucide-react';
import { Chatbot } from './Chatbot';
import { RightPanel } from './RightPanel';
import { useProblem } from '@/contexts/ProblemContext';
import { saveCode, getCode as getSavedCode } from '@/lib/userApi';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';

// Lazy load Monaco Editor for better initial load performance
const Editor = lazy(() => import('@monaco-editor/react'));

// Loading fallback for the editor
const EditorLoading = () => {
  const { theme } = useTheme();
  return (
    <div className="h-full flex items-center justify-center text-muted-foreground" style={{ backgroundColor: theme === 'dark' ? '#1e1e1e' : '#ffffff' }}>
      <Loader2 className="h-6 w-6 animate-spin mr-2" />
      <span>加载编辑器...</span>
    </div>
  );
};

// 当前编辑器中的代码（实时，用于 AI 聊天时获取）
let currentEditorCode = '';

export const getCurrentCode = () => currentEditorCode;

export const Workspace = memo(() => {
  const { currentProblem } = useProblem();
  const { theme, setTheme } = useTheme();
  const editorRef = useRef<any>(null);
  const [isLoadingCode, setIsLoadingCode] = useState(false);
  const [isSavingCode, setIsSavingCode] = useState(false);
  const [editorCode, setEditorCode] = useState('');  // 管理编辑器代码状态
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const problemTitle = currentProblem?.title || '请选择题目';
  const problemDifficulty = currentProblem?.difficulty || 'Easy';
  const problemTags = currentProblem?.tags || [];
  const problemContent = currentProblem?.problem_description || '';
  const testCases = currentProblem?.input_output || [];

  // 获取代码模板
  const getCodeTemplate = () => {
    return currentProblem?.starter_code || `class Solution:
    def solution(self):
        # Write your code here
        pass`;
  };

  // 从数据库加载用户保存的代码
  const loadSavedCode = async (problemId: string): Promise<string> => {
    setIsLoadingCode(true);
    try {
      const saved = await getSavedCode(problemId);
      if (saved?.code) {
        return saved.code;
      }
    } catch (error) {
      console.error('Failed to load saved code:', error);
    }
    return getCodeTemplate();
  };

  // 防抖保存代码到数据库
  const debouncedSaveCode = (problemId: string, code: string) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    setIsSavingCode(true);
    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await saveCode(problemId, code, 'python');
      } catch (error) {
        console.error('Failed to save code:', error);
      } finally {
        setIsSavingCode(false);
      }
    }, 1000); // 停止输入 1 秒后保存
  };

  // 切换题目时加载代码
  useEffect(() => {
    if (currentProblem) {
      loadSavedCode(currentProblem.task_id).then((code) => {
        setEditorCode(code);
        currentEditorCode = code;
        setIsLoadingCode(false);
      });
    }
  }, [currentProblem?.task_id]);

  // 更新 currentEditorCode 实时
  useEffect(() => {
    currentEditorCode = editorCode;
  }, [editorCode]);

  // 清理
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="h-full w-full bg-muted/10 overflow-hidden p-1">
         <ResizablePanelGroup direction="horizontal" className="h-full w-full">
            {/* 左侧：题目描述 + AI 助手 */}
            <ResizablePanel
                defaultSize="40"
                minSize="25"
                maxSize="50"
                collapsible={false}
                className="bg-card/80 backdrop-blur-sm rounded-lg border shadow-sm overflow-hidden"
            >
                <div className="h-full w-full flex flex-col overflow-hidden">
                    <Tabs defaultValue="description" className="h-full w-full flex flex-col">
                        <div className="border-b px-4 bg-background/50 shrink-0">
                             <TabsList className="h-10 bg-transparent p-0 w-full justify-start">
                                <TabsTrigger value="description" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-b-2 border-transparent data-[state=active]:border-primary px-4 gap-2">
                                    <BookOpen className="h-3.5 w-3.5" /> Description
                                </TabsTrigger>
                                <TabsTrigger value="chatbot" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none rounded-none border-b-2 border-transparent data-[state=active]:border-primary px-4 gap-2">
                                    <Bot className="h-3.5 w-3.5" /> AI Assistant
                                </TabsTrigger>
                            </TabsList>
                        </div>
                        <TabsContent value="description" className="flex-1 p-0 m-0 outline-none h-full overflow-hidden">
                            <ScrollArea className="h-full p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h1 className="text-2xl font-bold tracking-tight">{problemTitle}</h1>
                                    <div className="flex gap-2">
                                        <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400">
                                          {problemDifficulty}
                                        </Badge>
                                        {problemTags.map((tag) => (
                                            <Badge key={tag} variant="secondary" className="bg-secondary/50">{tag}</Badge>
                                        ))}
                                    </div>
                                </div>

                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    {problemContent ? (
                                        <div dangerouslySetInnerHTML={{ __html: problemContent }} />
                                    ) : (
                                        <p>暂无题目内容</p>
                                    )}

                                    <div className="my-6 space-y-4">
                                        {testCases.slice(0, 3).map((testCase, index) => (
                                            <div key={index} className="rounded-lg border bg-muted/30 p-4 shadow-sm">
                                                <h3 className="font-semibold mb-2 text-foreground">Example {index + 1}:</h3>
                                                <div className="font-mono text-xs space-y-1">
                                                    <div><span className="text-muted-foreground">Input:</span> {testCase.input || '—'}</div>
                                                    <div><span className="text-muted-foreground">Output:</span> {testCase.output || '—'}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                             </ScrollArea>
                        </TabsContent>
                        <TabsContent value="chatbot" className="flex-1 p-0 m-0 outline-none h-full overflow-hidden">
                            <Chatbot currentProblemId={currentProblem?.task_id || null} />
                        </TabsContent>
                    </Tabs>
                </div>
            </ResizablePanel>

            <ResizableHandle className="w-px bg-border" />

            {/* 右侧：代码编辑器 + 测试面板（上下布局） */}
            <ResizablePanel defaultSize="60" minSize="50">
                <ResizablePanelGroup direction="vertical" className="h-full">
                    {/* 上方：代码编辑器 */}
                    <ResizablePanel
                        defaultSize="65"
                        minSize="30"
                        className="rounded-lg border shadow-sm overflow-hidden"
                    >
                        <div className="h-full w-full flex flex-col overflow-hidden" style={{ backgroundColor: theme === 'dark' ? '#1e1e1e' : '#ffffff' }}>
                            <div className="h-10 border-b flex items-center px-4 justify-between shrink-0" style={{ backgroundColor: theme === 'dark' ? '#252526' : '#f3f3f3', borderColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }}>
                                 <div className="flex items-center gap-2 text-sm" style={{ color: theme === 'dark' ? '#858585' : '#6e6e6e' }}>
                                     <Code2 className="h-4 w-4" />
                                     <span className="font-medium" style={{ color: theme === 'dark' ? '#cccccc' : '#333333' }}>Solution.py</span>
                                 </div>
                                 <div className="flex items-center gap-3">
                                     {isSavingCode && (
                                       <div className="flex items-center gap-1 text-xs" style={{ color: theme === 'dark' ? '#858585' : '#6e6e6e' }}>
                                         <Loader2 className="h-3 w-3 animate-spin" />
                                         保存中...
                                       </div>
                                     )}
                                     <Button
                                         variant="ghost"
                                         size="icon"
                                         className="h-7 w-7"
                                         onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                                         title={theme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
                                     >
                                         {theme === 'dark' ? (
                                             <Sun className="h-4 w-4" />
                                         ) : (
                                             <Moon className="h-4 w-4" />
                                         )}
                                     </Button>
                                 </div>
                            </div>
                            <div className="flex-1">
                                <Suspense fallback={<EditorLoading />}>
                                    <Editor
                                    height="100%"
                                    defaultLanguage="python"
                                    theme={theme === 'dark' ? 'vs-dark' : 'light'}
                                    value={editorCode}
                                    onChange={(value) => {
                                      setEditorCode(value);
                                      if (currentProblem && value !== undefined) {
                                        currentEditorCode = value;
                                        debouncedSaveCode(currentProblem.task_id, value);
                                      }
                                    }}
                                    options={{
                                        minimap: { enabled: false },
                                        fontSize: 14,
                                        lineNumbers: 'on',
                                        scrollBeyondLastLine: false,
                                        automaticLayout: true,
                                        padding: { top: 16 },
                                        fontFamily: "'Fira Code', 'JetBrains Mono', Consolas, monospace",
                                        fontLigatures: true,
                                        smoothScrolling: true,
                                        cursorBlinking: "smooth",
                                        cursorSmoothCaretAnimation: "on"
                                    }}
                                />
                                </Suspense>
                            </div>
                        </div>
                    </ResizablePanel>

                    <ResizableHandle className="h-px bg-border flex flex-col" />

                    {/* 下方：测试用例 + 运行结果 */}
                    <ResizablePanel
                        defaultSize="35"
                        minSize="20"
                        collapsible={true}
                        className="bg-card/80 backdrop-blur-sm rounded-lg border shadow-sm overflow-hidden"
                    >
                        <RightPanel currentProblem={currentProblem} />
                    </ResizablePanel>
                </ResizablePanelGroup>
            </ResizablePanel>
         </ResizablePanelGroup>
    </div>
  );
});
