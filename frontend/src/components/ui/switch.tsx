import * as React from 'react'
import * as SwitchPrimitives from '@radix-ui/react-switch'

import { cn } from '@/lib/utils'

// Style the Root track using aria-checked instead of data-[state=...] because
// Radix Tooltip's TooltipTrigger (asChild) injects its own data-state onto the
// host element, overriding Switch's data-state and breaking the visual toggle.
// aria-checked is set by Radix Switch and is never overwritten by Tooltip.
// The Thumb is unaffected (Tooltip only decorates the trigger, not children).
//
// Disabled style: uses cursor-default (not cursor-not-allowed) for a subtle
// disabled appearance — tooltip remains functional.
const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(
      'peer focus-visible:ring-ring focus-visible:ring-offset-background bg-input aria-checked:bg-status-active inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-default disabled:opacity-50',
      className
    )}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        'pointer-events-none block h-5 w-5 rounded-full bg-white shadow-[0_2px_4px_rgba(0,0,0,0.2)] ring-0 transition-transform duration-200 data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0'
      )}
    />
  </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
