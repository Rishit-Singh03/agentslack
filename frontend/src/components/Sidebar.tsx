import { departmentStyle } from './DepartmentTag'
import type { Agent, Channel, Department, Org, View } from '../api/types'

export function Sidebar(p: {
  org: Org
  departments: Department[]
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
  newChannel: () => void
  flashes: number[]
}) {
  const departmentChannels = new Set(p.departments.map((department) => department.channel_id))
  const sharedChannels = p.channels.filter(
    (channel) => !channel.is_dm && !departmentChannels.has(channel.id),
  )
  return (
    <>
      {p.open && (
        <button className="sidebar-scrim" aria-label="Close navigation" onClick={p.close} />
      )}
      <aside className={`sidebar ${p.open ? 'is-open' : ''}`}>
        <div className="sidebar-heading">
          <button onClick={() => p.navigate('settings')}>{p.org.name}</button>
          <button className="mobile-close" onClick={p.close}>
            [x]
          </button>
        </div>
        {p.org.tagline && <p className="sidebar-tagline">{p.org.tagline}</p>}
        <nav aria-label="Workspace navigation">
          <h3>
            CHANNELS <span>{sharedChannels.length}</span>
          </h3>
          {sharedChannels.map((c) => (
            <button
              key={c.id}
              className={`nav-item ${p.view === 'channel' && p.active === c.id ? 'active' : ''}`}
              onClick={() => p.select(c)}
            >
              <span className="dim">#</span> {c.name}
            </button>
          ))}
          <button className="nav-item muted" onClick={p.newChannel}>
            + new channel
          </button>
          <h3>
            DEPARTMENTS <span>{p.departments.length}</span>
          </h3>
          {p.departments.map((department) => {
            const channel = p.channels.find((item) => item.id === department.channel_id)
            return (
              channel && (
                <button
                  key={department.id}
                  className={`nav-item ${p.view === 'channel' && p.active === channel.id ? 'active' : ''}`}
                  onClick={() => p.select(channel)}
                >
                  <span className="department-marker" style={departmentStyle(department)} />
                  <span className="department-nav-name">{department.name}</span>
                </button>
              )
            )
          })}
          <h3>
            DIRECT <span>{p.agents.length}</span>
          </h3>
          {p.agents.map((a) => (
            <button
              key={a.id}
              className={`nav-item ${p.view === 'channel' && p.channels.find((c) => c.id === p.active)?.dm_agent_id === a.id ? 'active' : ''}`}
              onClick={() => p.dm(a)}
            >
              <span className={`status ${a.status}`}>
                {a.status === 'online' || a.status === 'busy' ? '●' : '○'}
              </span>{' '}
              <span
                className={`handle department-handle ${p.flashes.includes(a.id) ? 'level-flash' : ''}`}
                style={departmentStyle(
                  p.departments.find((department) => department.id === a.department_id),
                )}
              >
                {a.handle.slice(1)}
              </span>
              <small>
                {p.departments.find((department) => department.id === a.department_id)?.slug ??
                  'unassigned'}
              </small>
            </button>
          ))}
          <button className="nav-item muted" onClick={p.hire}>
            + hire agent
          </button>
          <h3>WORKSPACE</h3>
          {(['tasks', 'agents', 'activity', 'settings'] as const).map((view) => (
            <button
              key={view}
              className={`nav-item ${p.view === view ? 'active' : ''}`}
              onClick={() => p.navigate(view)}
            >
              {view}
              <span className="nav-key">
                {view === 'tasks' ? '[n]' : view === 'settings' ? '[,]' : ''}
              </span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>chat workspace</span>
          <button onClick={() => p.navigate('activity')}>[tail -f]</button>
        </div>
      </aside>
    </>
  )
}
