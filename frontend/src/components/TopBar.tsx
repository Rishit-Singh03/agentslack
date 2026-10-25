import { Menu, Moon, Sparkles, Sun } from 'lucide-react'
import type { Agent, Channel } from '../api/types'
import { SearchBox } from './SearchBox'

interface TopBarProps {
  agents: Agent[]
  channels: Channel[]
  connected: boolean
  theme: string
  toggleTheme: () => void
  openNavigation: () => void
  selectChannel: (channel: Channel) => void
  selectAgent: (agent: Agent) => void
}

export function TopBar({
  agents,
  channels,
  connected,
  theme,
  toggleTheme,
  openNavigation,
  selectChannel,
  selectAgent,
}: TopBarProps) {
  return (
    <header className="topbar">
      <button
        className="mobile-menu icon-button"
        onClick={openNavigation}
        aria-label="Open navigation"
      >
        <Menu size={21} />
      </button>
      <div className="brand">
        <Sparkles size={18} />
        <span>agentslack</span>
        <span className="beta">BETA</span>
      </div>
      <SearchBox
        agents={agents}
        channels={channels}
        selectChannel={selectChannel}
        selectAgent={selectAgent}
      />
      <div className="topbar-right">
        <span className={`connection ${connected ? '' : 'disconnected'}`}>
          <span className="tiny-dot" />
          {connected ? 'Connected' : 'Reconnecting…'}
        </span>
        <button
          className="icon-button"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <span className="your-avatar" title="You · workspace owner">
          Y
        </span>
      </div>
    </header>
  )
}
