import { Menu } from 'lucide-react'
import type { Org, UserProfile } from '../api/types'

export function TopBar({
  org,
  me,
  connected,
  palette,
  settings,
  openNavigation,
}: {
  org: Org
  me: UserProfile
  connected: boolean
  palette: () => void
  settings: () => void
  openNavigation: () => void
}) {
  return (
    <header className="topbar">
      <button
        className="mobile-menu icon-button"
        onClick={openNavigation}
        aria-label="Open navigation"
      >
        <Menu size={14} strokeWidth={1.5} />
      </button>
      <span className="brand">agentslack</span>
      <span className="dim">/</span>
      <button className="org-name" onClick={settings}>
        {org.slug}
      </button>
      <button className="palette-trigger" onClick={palette}>
        find or run a command <kbd>Ctrl K</kbd>
      </button>
      <span className={`connection ${connected ? 'ok' : 'warn'}`}>
        {connected ? '● connected' : '○ disconnected'}
      </span>
      <button onClick={settings} className="profile-trigger">
        [{me.handle.slice(1)}]
      </button>
    </header>
  )
}
