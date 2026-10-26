import { DepartmentSelect } from './DepartmentSelect'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Agent, Department } from '../api/types'
import { EmploymentFields, employmentFromForm } from './EmploymentFields'

export function AgentEditForm({
  agent,
  saved,
  departments,
}: {
  agent: Agent
  saved: (agent: Agent) => void
  departments: Department[]
}) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true)
    try {
      saved(
        await api.updateAgent(agent.id, {
          ...employmentFromForm(data),
          name: String(data.get('name')),
          title: String(data.get('title')),
          department_id: data.get('department_id') ? Number(data.get('department_id')) : null,
          bio: String(data.get('bio')),
          skills: String(data.get('skills'))
            .split(',')
            .map((skill) => skill.trim())
            .filter(Boolean),
          avatar_color: String(data.get('color')),
        }),
      )
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <form className="pane-form" onSubmit={submit}>
      <label>
        Name
        <input name="name" defaultValue={agent.name} required maxLength={100} />
      </label>
      <label>
        Title
        <input name="title" defaultValue={agent.title} required maxLength={150} />
      </label>
      <DepartmentSelect departments={departments} value={agent.department_id} />
      <label>
        Bio
        <textarea name="bio" rows={3} defaultValue={agent.bio} />
      </label>
      <label>
        Skills (comma separated)
        <input name="skills" defaultValue={agent.skills.join(', ')} />
      </label>
      <label>
        Color
        <input name="color" defaultValue={agent.avatar_color} pattern="#[0-9a-fA-F]{6}" required />
      </label>
      <p className="dim">
        Color is stored as profile metadata. Workspace chrome uses the org accent.
      </p>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <EmploymentFields agent={agent} />
      <button className="primary-button" disabled={busy}>
        Save agent
      </button>
    </form>
  )
}
