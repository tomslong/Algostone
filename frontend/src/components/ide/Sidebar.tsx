import React, { useEffect, useState, memo, useCallback } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, Folder, FileCode, ChevronRight, ChevronDown, Loader2, PanelLeft, CheckCircle2 } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useProblem } from '@/contexts/ProblemContext';
import { API_ENDPOINTS } from '@/config';
import { getDeviceId } from '@/lib/device';
import axios from 'axios';

interface SidebarProps {
    onCollapse?: () => void;
    isCollapsed?: boolean;
}

export const Sidebar = memo(({ onCollapse, isCollapsed }: SidebarProps) => {
    const { problems, selectProblem, currentProblem, loading } = useProblem();
    const [searchTerm, setSearchTerm] = useState('');
    const [acProblems, setAcProblems] = useState<Set<string>>(new Set());
    const [openSections, setOpenSections] = useState<Record<string, boolean>>({
        'easy': true,
        'medium': true,
        'hard': false
    });

    // 获取已通过的题目
    useEffect(() => {
        const fetchAcProblems = async () => {
            try {
                const deviceId = getDeviceId();
                const response = await axios.get(API_ENDPOINTS.AC_PROBLEMS(deviceId));
                const acList = response.data.ac_problems || [];
                setAcProblems(new Set(acList));
            } catch (error) {
                console.error('Failed to fetch AC problems:', error);
            }
        };
        fetchAcProblems();
    }, []);

  const toggleSection = (section: string) => {
      setOpenSections(prev => ({...prev, [section]: !prev[section]}));
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const filteredProblems = problems.filter((problem) => {
    if (!normalizedSearch) return true;
    return (
      problem.title?.toLowerCase().includes(normalizedSearch) ||
      problem.task_id?.toLowerCase().includes(normalizedSearch)
    );
  });

  const easyProblems = filteredProblems.filter((p) => p.difficulty === 'Easy');
  const mediumProblems = filteredProblems.filter((p) => p.difficulty === 'Medium');
  const hardProblems = filteredProblems.filter((p) => p.difficulty === 'Hard');

  const renderProblemItem = (problemId: string, title: string, isActive: boolean) => {
    const isAc = acProblems.has(problemId);
    return (
      <Button
        key={problemId}
        variant={isActive ? 'secondary' : 'ghost'}
        size="sm"
        className={cn(
          "w-full justify-start h-8 font-normal px-1 min-w-0 overflow-hidden gap-1",
          isActive ? "text-foreground" : "text-muted-foreground"
        )}
        onClick={() => selectProblem(problemId)}
      >
        {isAc && (
          <CheckCircle2 className="flex-none h-3 w-3 text-green-500" />
        )}
        <FileCode className="flex-none h-3 w-3 opacity-70" />
        <span className="truncate flex-1 text-left min-w-0">
          {title}
        </span>
      </Button>
    );
  };

  return (
    <div className="h-full w-full flex flex-col bg-card/30 min-w-0 overflow-hidden">
        {/* Header - always visible */}
        <div className="w-full p-4 border-b space-y-3 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Problems</h2>
            {onCollapse && (
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0"
                    onClick={onCollapse}
                >
                    <PanelLeft className="h-4 w-4" />
                </Button>
            )}
        </div>

        {/* Content - hide when collapsed */}
        {!isCollapsed && (
            <>
                <div className="w-full px-4 pb-4">
                    <div className="relative w-full">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search..."
                          className="pl-8 h-9 text-sm w-full"
                          value={searchTerm}
                          onChange={(event) => setSearchTerm(event.target.value)}
                        />
                    </div>
                </div>
                <ScrollArea className="flex-1 w-full">
            <div className="p-2 space-y-1 w-full overflow-hidden">
                {loading && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground px-2 py-2 w-full">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在加载题目...
                  </div>
                )}
                {/* Easy Section */}
                <Collapsible
                    open={openSections['easy']}
                    onOpenChange={() => toggleSection('easy')}
                    className="group/collapsible"
                >
                    <CollapsibleTrigger asChild>
                         <Button variant="ghost" className="w-full justify-start hover:bg-accent/50 h-9 min-w-0 px-1 gap-1">
                            <Folder className="flex-none h-4 w-4 text-green-500" />
                            <span className="truncate flex-1 text-left min-w-0">Easy</span>
                            <Badge variant="outline" className="flex-none text-[10px] h-4 px-1 border-green-500/30 text-green-500">
                              {easyProblems.length}
                            </Badge>
                            <span className="flex-none">
                              {openSections['easy'] ? <ChevronDown className="h-3 w-3 opacity-50"/> : <ChevronRight className="h-3 w-3 opacity-50"/>}
                            </span>
                         </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pl-4 space-y-1 py-1 w-full overflow-hidden">
                        {easyProblems.map((problem) =>
                          renderProblemItem(
                            problem.task_id,
                            problem.title,
                            currentProblem?.task_id === problem.task_id
                          )
                        )}
                    </CollapsibleContent>
                </Collapsible>

                 {/* Medium Section */}
                 <Collapsible
                    open={openSections['medium']}
                    onOpenChange={() => toggleSection('medium')}
                    className="group/collapsible"
                >
                    <CollapsibleTrigger asChild>
                         <Button variant="ghost" className="w-full justify-start hover:bg-accent/50 h-9 min-w-0 px-1 gap-1">
                            <Folder className="flex-none h-4 w-4 text-yellow-500" />
                            <span className="truncate flex-1 text-left min-w-0">Medium</span>
                            <Badge variant="outline" className="flex-none text-[10px] h-4 px-1 border-yellow-500/30 text-yellow-500">
                              {mediumProblems.length}
                            </Badge>
                            <span className="flex-none">
                              {openSections['medium'] ? <ChevronDown className="h-3 w-3 opacity-50"/> : <ChevronRight className="h-3 w-3 opacity-50"/>}
                            </span>
                         </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pl-4 space-y-1 py-1 w-full overflow-hidden">
                        {mediumProblems.map((problem) =>
                          renderProblemItem(
                            problem.task_id,
                            problem.title,
                            currentProblem?.task_id === problem.task_id
                          )
                        )}
                    </CollapsibleContent>
                </Collapsible>

                {/* Hard Section */}
                 <Collapsible
                    open={openSections['hard']}
                    onOpenChange={() => toggleSection('hard')}
                    className="group/collapsible"
                >
                    <CollapsibleTrigger asChild>
                         <Button variant="ghost" className="w-full justify-start hover:bg-accent/50 h-9 min-w-0 px-1 gap-1">
                            <Folder className="flex-none h-4 w-4 text-red-500" />
                            <span className="truncate flex-1 text-left min-w-0">Hard</span>
                            <Badge variant="outline" className="flex-none text-[10px] h-4 px-1 border-red-500/30 text-red-500">
                              {hardProblems.length}
                            </Badge>
                            <span className="flex-none">
                              {openSections['hard'] ? <ChevronDown className="h-3 w-3 opacity-50"/> : <ChevronRight className="h-3 w-3 opacity-50"/>}
                            </span>
                         </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pl-4 space-y-1 py-1 w-full overflow-hidden">
                        {hardProblems.map((problem) =>
                          renderProblemItem(
                            problem.task_id,
                            problem.title,
                            currentProblem?.task_id === problem.task_id
                          )
                        )}
                    </CollapsibleContent>
                </Collapsible>
            </div>
        </ScrollArea>
            </>
        )}
    </div>
  );
});
