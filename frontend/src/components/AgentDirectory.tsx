import type { Agent, Department } from '../api/types'
import { departmentStyle } from './DepartmentTag'

export function AgentDirectory({
  agents,
  departments,
  profile,
  hire,
}: {
  agents: Agent[]
  departments: Department[]
  profile: (agent: Agent) => void
  hire: () => void
}) {
  const groups = [
    ...departments.map((department) => ({
      department,
      agents: agents.filter((agent) => agent.department_id === department.id),
    })),
    {
      department: undefined,
      agents: agents.filter(
        (agent) =>
          agent.department_id === null ||
          !departments.some((department) => department.id === agent.department_id),
      ),
    },
  ]
  return (
    <>
      <header className="view-header">
        <h1>agents</h1>
        <span className="topic">
          {agents.length} registered / {departments.length} departments
        </span>
        <button className="header-action" onClick={hire}>
          [+] hire agent
        </button>
      </header>
      <div className="directory">
        {groups.map((group) => (
          <section className="agent-group" key={group.department?.id ?? 'unassigned'}>
            <h2 style={departmentStyle(group.department)}>
              <span className="department-marker" />
              {group.department?.name ?? 'Unassigned'}{' '}
              <span className="dim">({group.agents.length})</span>
            </h2>
            {group.agents.map((agent) => (
              <button className="agent-row" key={agent.id} onClick={() => profile(agent)}>
                <span>
                  <strong
                    className="handle department-handle"
                    style={departmentStyle(group.department)}
                  >
                    {agent.handle}
                  </strong>
                  <small>{agent.name}</small>
                </span>
                <span>
                  {agent.title}
                  <small>{agent.skills.join(' / ') || 'No skills set'}</small>
                </span>
                <span>
                  lvl {agent.level} / {agent.xp}xp
                  <small className={`status ${agent.status}`}>{agent.status}</small>
                </span>
              </button>
            ))}
            {!group.agents.length && <p className="group-empty">No agents assigned.</p>}
          </section>
        ))}
      </div>
    </>
  )
}
