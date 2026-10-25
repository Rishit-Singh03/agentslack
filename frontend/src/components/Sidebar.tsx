import { Bot, ChevronDown, Hash, LayoutGrid, ListTodo, Plus, Sparkles, X } from 'lucide-react'
import type { Agent, Channel } from '../api/types'
import { AgentAvatar } from './AgentAvatar'

export type View = 'channel' | 'tasks' | 'agents'
interface Props {
  agents: Agent[]
  channels: Channel[]
  active: number | null
  view: View
  open: boolean
  close: () => void
  navigate: (view: View) => void
  select: (channel: Channel) => void
  dm: (agent: Agent) => void
  hire: () => void
}
export function Sidebar(p: Props) {
  return (
    <>
      <div className={`sidebar-scrim ${p.open ? 'visible' : ''}`} onClick={p.close} />
      <aside className={`sidebar ${p.open ? 'is-open' : ''}`}>
        <button
          className="workspace"
          title="Acme Agents · workspace switching is coming in a later phase"
        >
          <span className="workspace-mark">
            <Sparkles size={22} />
          </span>
          <span>
            Acme Agents<small>Your AI workspace</small>
          </span>
          <ChevronDown size={16} />
        </button>
        <button
          className="mobile-close icon-button"
          onClick={p.close}
          aria-label="Close navigation"
        >
          <X size={18} />
        </button>
        <div className="workspace-caption">
          <span className="tiny-dot" /> A little team. A lot of possibility.
        </div>
        <nav aria-label="Workspace navigation">
          <button
            className={`nav-item ${p.view === 'tasks' ? 'active' : ''}`}
            onClick={() => p.navigate('tasks')}
          >
            <ListTodo size={18} />
            Tasks<span className="nav-hint">Board</span>
          </button>
          <button
            className={`nav-item ${p.view === 'agents' ? 'active' : ''}`}
            onClick={() => p.navigate('agents')}
          >
            <LayoutGrid size={18} />
            Agent directory<span className="count">{p.agents.length}</span>
          </button>
          <div className="nav-section">
            <ChevronDown size={13} />
            Channels
          </div>
          {p.channels
            .filter((c) => !c.is_dm)
            .map((c) => (
              <button
                key={c.id}
                className={`nav-item channel-nav ${p.view === 'channel' && p.active === c.id ? 'active' : ''}`}
                onClick={() => p.select(c)}
              >
                <Hash size={18} />
                {c.name}
                {c.name === 'general' && <span className="channel-spark">✧</span>}
              </button>
            ))}
          <div className="nav-section">
            <ChevronDown size={13} />
            Direct messages<span className="count">{p.agents.length}</span>
          </div>
          {p.agents.map((a) => (
            <button
              key={a.id}
              onClick={() => p.dm(a)}
              className={`nav-item dm-nav ${p.view === 'channel' && p.channels.find((c) => c.id === p.active)?.dm_agent_id === a.id ? 'active' : ''}`}
            >
              <AgentAvatar agent={a} size={26} />
              <span>{a.name}</span>
              <span className="agent-role-short">{a.role}</span>
            </button>
          ))}
          <button className="hire-sidebar" onClick={p.hire}>
            <Plus size={16} /> Hire an agent
          </button>
        </nav>
        <div className="sidebar-bottom">
          <span className="stub-symbol">
            <Bot size={18} />
          </span>
          <div>
            Built for your next big thing<small>Phase 1 · Stub agents</small>
          </div>
        </div>
      </aside>
    </>
  )
}
