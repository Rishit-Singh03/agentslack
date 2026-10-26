import { DepartmentTag, departmentStyle } from './DepartmentTag'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Agent, Department, MemoryEntry, Task } from '../api/types'
import { AgentEditForm } from './AgentEditForm'
import { EmploymentSummary } from './EmploymentSummary'

export function AgentProfile({
  agent,
  tasks,
  close,
  dm,
  changed,
  dismissed,
  departments,
}: {
  agent: Agent
  departments: Department[]
  tasks: Task[]
  close: () => void
  dm: (agent: Agent) => void
  changed: (agent: Agent) => void
  dismissed: (id: number) => void
}) {
  const [memory, setMemory] = useState<MemoryEntry[]>([])
  const [editing, setEditing] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    setEditing(false)
    setConfirm(false)
    setError('')
    let alive = true
    api
      .memory(agent.id)
      .then((entries) => {
        if (alive) setMemory(entries)
      })
      .catch(() => {
        if (alive) setError('Memory unavailable')
      })
    return () => {
      alive = false
    }
  }, [agent.id])
  const dismiss = async () => {
    try {
      await api.deleteAgent(agent.id)
      dismissed(agent.id)
      close()
    } catch (error) {
      setError((error as Error).message)
    }
  }
  const department = departments.find((item) => item.id === agent.department_id)
  const active = tasks.filter(
    (task) => task.assignee_agent_id === agent.id && task.status !== 'done',
  )
  return (
    <aside className="info-pane">
      <header>
        <h2>agent / {agent.handle}</h2>
        <button onClick={close} aria-label="Close profile">
          [x]
        </button>
      </header>
      <div className="pane-scroll">
        <section>
          <h3 className="handle department-handle" style={departmentStyle(department)}>
            {agent.handle}
          </h3>
          <p>
            {agent.name} - {agent.title}
          </p>
          <p className={`status ${agent.status}`}>
            ● {agent.status} <DepartmentTag department={department} />
          </p>
          <div className="pane-actions">
            <button onClick={() => dm(agent)}>[message]</button>
            <button onClick={() => setEditing(!editing)}>
              [{editing ? 'cancel edit' : 'edit'}]
            </button>
          </div>
        </section>
        {editing && (
          <AgentEditForm
            key={agent.id}
            agent={agent}
            departments={departments}
            saved={(updated) => {
              changed(updated)
              setEditing(false)
            }}
          />
        )}
        <section>
          <h3>ABOUT</h3>
          <p>{agent.bio || 'No bio set.'}</p>
        </section>
        {!editing && <EmploymentSummary agent={agent} />}
        <section>
          <h3>PROGRESS</h3>
          <p>
            lvl {agent.level} / {agent.xp}xp
          </p>
          <div className="xp-track">
            <span style={{ width: `${agent.xp % 100}%` }} />
          </div>
          <p className="dim">
            {100 - (agent.xp % 100)}xp to lvl {agent.level + 1}
          </p>
        </section>
        <section>
          <h3>SKILLS</h3>
          <p>
            {agent.skills.length
              ? agent.skills.map((skill) => `[${skill}]`).join(' ')
              : 'No skills set.'}
          </p>
        </section>
        <section>
          <h3>CURRENT TASKS ({active.length})</h3>
          {active.map((task) => (
            <p className="profile-task" key={task.id}>
              #{task.id} {task.title}
              <small>{task.status}</small>
            </p>
          ))}
          {!active.length && <p className="dim">No active tasks.</p>}
        </section>
        <section>
          <h3>MEMORY</h3>
          {memory.length ? (
            memory.map((entry) => <p key={entry.id}>{entry.content}</p>)
          ) : (
            <p className="dim">No memory entries. Persistent learning is not connected.</p>
          )}
        </section>
        <section>
          <h3>MANAGE</h3>
          {confirm ? (
            <div>
              <p>
                Dismiss {agent.handle}? Assigned tasks and its DM history will be deleted. Shared
                channel messages are retained.
              </p>
              <div className="pane-actions">
                <button className="danger" onClick={() => void dismiss()}>
                  [confirm dismiss]
                </button>
                <button onClick={() => setConfirm(false)}>[cancel]</button>
              </div>
            </div>
          ) : (
            <button className="danger" onClick={() => setConfirm(true)}>
              [dismiss agent]
            </button>
          )}
        </section>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </aside>
  )
}
