import React, { useState, useRef, memo } from 'react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { PanelLeftOpen } from "lucide-react";
import { Sidebar } from './Sidebar';
import { Workspace } from './Workspace';
import { cn } from '@/lib/utils';

export const IDELayout = memo(() => {
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const sidebarRef = useRef<React.ElementRef<typeof ResizablePanel>>(null);

    const collapseSidebar = () => {
        sidebarRef.current?.collapse();
    };

    return (
        <div className="h-screen w-screen overflow-hidden bg-background flex flex-col">
            <div className="flex-1 overflow-hidden relative">
                <div className="absolute inset-0 bg-grid-pattern opacity-[0.02] pointer-events-none" />
                <ResizablePanelGroup direction="horizontal" className="h-full w-full">
                    {/* App Sidebar - Leftmost */}
                    <ResizablePanel
                        ref={sidebarRef}
                        defaultSize="18"
                        minSize="0"
                        maxSize="30"
                        collapsible={true}
                        collapsedSize={0}
                        onCollapse={() => setIsSidebarCollapsed(true)}
                        onExpand={() => setIsSidebarCollapsed(false)}
                        className={cn(
                            "transition-all duration-300 ease-in-out z-20",
                            "bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
                        )}
                    >
                        <Sidebar onCollapse={collapseSidebar} isCollapsed={isSidebarCollapsed} />
                    </ResizablePanel>

                    <ResizableHandle
                        className={cn(
                            "transition-all duration-300 bg-border/50 w-px",
                            isSidebarCollapsed ? "w-0 opacity-0" : "w-px"
                        )}
                    />

                    {/* Main Workspace Area */}
                    <ResizablePanel defaultSize="75" className="z-10">
                        <Workspace />
                    </ResizablePanel>
                </ResizablePanelGroup>

                {/* Floating Expand Button - Rendered last to ensure it's on top */}
                {isSidebarCollapsed && (
                    <div className="absolute top-4 left-4 z-[100] animate-in fade-in zoom-in duration-300">
                        <Button
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 bg-background shadow-md hover:bg-accent border border-border/50"
                            onClick={() => sidebarRef.current?.expand()}
                        >
                            <PanelLeftOpen className="h-4 w-4" />
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
});
