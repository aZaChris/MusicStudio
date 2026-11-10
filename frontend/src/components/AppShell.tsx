import type { ReactNode } from 'react'

import { Sidebar } from './Sidebar'

/** Plum sidebar on the left, the page on the right. Stacks on narrow screens. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <div className="app-side">
        <Sidebar />
      </div>
      <main className="app-main">{children}</main>
    </div>
  )
}
