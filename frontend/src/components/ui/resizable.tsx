import { GripVertical } from "lucide-react"
import { Group, Panel, Separator, PanelImperativeHandle, PanelProps } from "react-resizable-panels"
import * as React from "react"
import { cn } from "../../lib/utils"

const ResizablePanelGroup = ({
  className,
  direction = "horizontal",
  ...props
}: React.ComponentProps<typeof Group> & { direction?: "horizontal" | "vertical" }) => (
  <Group
    orientation={direction}
    className={cn(
      "flex h-full w-full data-[panel-group-direction=vertical]:flex-col",
      direction === "vertical" ? "flex-col" : "flex-row",
      className
    )}
    {...props}
  />
)

interface ExtendedPanelProps extends React.ComponentProps<typeof Panel> {
  onCollapse?: () => void;
  onExpand?: () => void;
}

const ResizablePanel = React.forwardRef<
  PanelImperativeHandle,
  ExtendedPanelProps
>(({ className, onCollapse, onExpand, onResize, ...props }, ref) => {
  const isCollapsedRef = React.useRef(false)

  const handleResize: PanelProps['onResize'] = (size, id, prevSize) => {
    if (onResize) onResize(size, id, prevSize)
    
    // Assuming collapsed if size is very small (close to 0)
    // This is a heuristic since we don't know the exact collapsed state from size alone easily
    // without knowing collapsedSize prop value which defaults to 0
    const isCollapsed = size.inPixels === 0
    
    if (isCollapsed !== isCollapsedRef.current) {
      isCollapsedRef.current = isCollapsed
      if (isCollapsed && onCollapse) onCollapse()
      if (!isCollapsed && onExpand) onExpand()
    }
  }

  return (
    <Panel
      panelRef={ref}
      className={cn(
        "flex h-full w-full data-[panel-group-direction=vertical]:h-auto",
        className
      )}
      onResize={handleResize}
      {...props}
    />
  )
})
ResizablePanel.displayName = "ResizablePanel"

const ResizableHandle = ({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof Separator> & {
  withHandle?: boolean
}) => (
  <Separator
    className={cn(
      "relative flex w-4 items-center justify-center bg-transparent transition-all",
      "after:absolute after:inset-y-0 after:left-1/2 after:w-[1px] after:-translate-x-1/2 after:bg-border/50 after:transition-all after:duration-300",
      "hover:after:w-[2px] hover:after:bg-primary",
      "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1",
      // Vertical Group (Horizontal Separator) styles - supporting both data attribute and aria-orientation
      "data-[panel-group-direction=vertical]:h-4 data-[panel-group-direction=vertical]:w-full",
      "&[aria-orientation=horizontal]:h-4 &[aria-orientation=horizontal]:w-full",
      
      "data-[panel-group-direction=vertical]:after:left-0 data-[panel-group-direction=vertical]:after:h-[1px] data-[panel-group-direction=vertical]:after:w-full data-[panel-group-direction=vertical]:after:-translate-y-1/2 data-[panel-group-direction=vertical]:after:translate-x-0",
      "&[aria-orientation=horizontal]:after:left-0 &[aria-orientation=horizontal]:after:h-[1px] &[aria-orientation=horizontal]:after:w-full &[aria-orientation=horizontal]:after:-translate-y-1/2 &[aria-orientation=horizontal]:after:translate-x-0 &[aria-orientation=horizontal]:after:inset-x-0 &[aria-orientation=horizontal]:after:top-1/2",
      
      "data-[panel-group-direction=vertical]:hover:after:h-[2px]",
      "&[aria-orientation=horizontal]:hover:after:h-[2px]",
      
      "[&[data-panel-group-direction=vertical]>div]:rotate-90",
      "[&[aria-orientation=horizontal]>div]:rotate-90",
      
      className
    )}
    {...props}
  >
    {withHandle && (
      <div className="z-10 flex h-8 w-4 items-center justify-center rounded-full border bg-background shadow-md transition-all hover:scale-110 hover:border-primary/50">
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </div>
    )}
  </Separator>
)

export { ResizablePanelGroup, ResizablePanel, ResizableHandle }
