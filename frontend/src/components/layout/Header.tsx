/**
 * App header component with layout controls.
 * Supports dashboard view and session view (sidebar toggle + Normal/Browser layout switch).
 */
import { useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { SettingsDialog, SettingsTrigger } from '@/components/settings'
import { NotificationCenter } from './NotificationCenter'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useUIStore } from '@/stores'
import type { SessionLayout } from '@/stores/uiStore'
import { useResponsiveLayout } from '@/hooks'
import { PanelLeftClose, PanelLeftOpen, LayoutGrid, Plus } from 'lucide-react'

export type AppLayout = 'dashboard' | 'sidebar-show' | 'sidebar-hide'

export interface HeaderProps {
  layout: AppLayout
  /** Optional slot for bottom content (e.g., tabs in dashboard) */
  bottomSlot?: ReactNode
  onNewSession: () => void
  /** Disable the New Session button (e.g., when a draft session is already selected) */
  newSessionDisabled?: boolean
  onToggleSidebar?: () => void
  onBackToDashboard?: () => void
}

export function Header({
  layout,
  bottomSlot,
  onNewSession,
  newSessionDisabled,
  onToggleSidebar,
  onBackToDashboard,
}: HeaderProps) {
  const isDashboard = layout === 'dashboard'
  const isSidebarVisible = layout === 'sidebar-show'
  const hasBottomSlot = !!bottomSlot
  const sessionLayout = useUIStore((s) => s.sessionLayout)
  const setSessionLayout = useUIStore((s) => s.setSessionLayout)

  // Use same breakpoint as sidebar visibility (820px = SIDEBAR + CHAT_MIN)
  const { allowSidebar } = useResponsiveLayout()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const openSettings = () => setSettingsOpen(true)

  const AppTitle = (
    // Session view on phones: no room for the name next to the controls
    <div className={cn('shrink-0 items-center gap-2', isDashboard ? 'flex' : 'hidden sm:flex')}>
      <span className="text-foreground text-base leading-none tracking-tight">
        <span className="font-bold">Magentic</span>
        <span className="font-light">Lite</span>
      </span>
    </div>
  )

  const SidebarToggleButton = !isDashboard ? (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="secondary"
          size="icon"
          className="size-8"
          onClick={onToggleSidebar}
          aria-label={isSidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
        >
          {isSidebarVisible ? (
            <PanelLeftClose className="size-4" />
          ) : (
            <PanelLeftOpen className="size-4" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{isSidebarVisible ? 'Hide sidebar' : 'Show sidebar'}</TooltipContent>
    </Tooltip>
  ) : null

  const DashboardButton = !isDashboard ? (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="secondary"
          size="icon"
          className="size-8"
          onClick={onBackToDashboard}
          aria-label="Back to dashboard"
        >
          <LayoutGrid className="size-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>Back to dashboard</TooltipContent>
    </Tooltip>
  ) : null

  const NewSessionButton = (
    <Button
      onClick={onNewSession}
      disabled={newSessionDisabled}
      aria-label="New Session"
      className="max-sm:w-9 max-sm:px-0"
    >
      <Plus className="size-4" />
      <span className="hidden sm:inline">New Session</span>
    </Button>
  )

  // Normal | Browser layout switch, session view only
  const LayoutSwitch = !isDashboard ? (
    <Tabs value={sessionLayout} onValueChange={(v) => setSessionLayout(v as SessionLayout)}>
      <TabsList aria-label="Session layout">
        <TabsTrigger value="normal" className="px-3 text-xs">
          Normal
        </TabsTrigger>
        <TabsTrigger value="browser" className="px-3 text-xs">
          Browser
        </TabsTrigger>
      </TabsList>
    </Tabs>
  ) : null

  return (
    <header className="border-sidebar-border bg-sidebar w-full border-b">
      <div className="flex h-[52px] items-center gap-2 px-3 sm:gap-3 sm:px-4">
        {allowSidebar && sessionLayout === 'normal' && SidebarToggleButton}
        {DashboardButton}
        {AppTitle}
        <div className="flex-1" />
        {LayoutSwitch}
        {NewSessionButton}
        <NotificationCenter />
        <SettingsTrigger onClick={openSettings} />
      </div>

      {hasBottomSlot && <div className="flex justify-center pb-3">{bottomSlot}</div>}

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  )
}
