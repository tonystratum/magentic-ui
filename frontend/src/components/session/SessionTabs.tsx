/**
 * SessionTabs Component
 *
 * Horizontal session strip used in the browser-first layout in place of the Sidebar.
 */
import { cn } from '@/lib/utils'
import { SESSION_STATUS_UI_CONFIG } from '@/lib/constants'
import type { UISession } from '@/types'

export interface SessionTabsProps {
  sessions: UISession[]
  selectedSessionId?: number
  onSessionSelect?: (id: number) => void
}

export function SessionTabs({ sessions, selectedSessionId, onSessionSelect }: SessionTabsProps) {
  return (
    <nav
      aria-label="Session history"
      className="border-sidebar-border flex shrink-0 gap-1.5 overflow-x-auto border-b px-4 py-2"
    >
      {sessions.map((session) => {
        const config = SESSION_STATUS_UI_CONFIG[session.status]
        const selected = session.id === selectedSessionId
        return (
          <button
            key={session.id}
            type="button"
            aria-current={selected ? 'page' : undefined}
            title={`${session.title} · ${config.cardLabel}`}
            onClick={() => onSessionSelect?.(session.id)}
            className={cn(
              'flex h-8 max-w-[220px] shrink-0 items-center gap-2 rounded-full px-3 text-xs',
              'focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none',
              selected
                ? 'bg-sidebar-accent text-foreground font-bold'
                : 'border-border text-foreground hover:bg-card-hover border'
            )}
          >
            <span className={cn('size-2 shrink-0 rounded-full', config.dotColorClass)} />
            <span className="truncate">{session.title}</span>
          </button>
        )
      })}
    </nav>
  )
}
