import { DepartmentSelect } from './DepartmentSelect'
import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Agent, Department } from '../api/types'
import { Modal } from './Modal'

export function HireAgentModal({
  close,
  hired,
  departments,
}: {
  close: () => void
  hired: (a: Agent) => void
  departments: Department[]
}) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setBusy(true)
    setError('')
    try {
      const name = String(data.get('name')).trim()
      const handle = String(data.get('handle')).trim().toLowerCase()
      hired(
        await api.hire({
          name,
          handle: handle.startsWith('@') ? handle : `@${handle}`,
          department_id: data.get('department_id') ? Number(data.get('department_id')) : null,
          title: String(data.get('title')).trim(),
          bio: String(data.get('bio')).trim(),
          skills: String(data.get('skills'))
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      )
      close()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal
      title="hire agent"
      subtitle="Add a specialist. Model defaults follow the department; edit Employment after hiring."
      close={close}
    >
      <form onSubmit={submit}>
        <div className="form-row">
          <label>
            Name
            <input name="name" required maxLength={100} placeholder="e.g. Alex" />
          </label>
          <label>
            Handle
            <input
              name="handle"
              required
              pattern="@?[a-zA-Z][a-zA-Z0-9_]{0,30}"
              placeholder="@alex"
            />
          </label>
        </div>
        <div className="form-row">
          <DepartmentSelect departments={departments} />
          <label>
            Title
            <input name="title" required maxLength={150} placeholder="e.g. Operations Manager" />
          </label>
        </div>
        <label>
          Skills <span>(comma separated)</span>
          <input name="skills" placeholder="Planning, Coordination, Reporting" />
        </label>
        <label>
          Bio
          <textarea name="bio" placeholder="Role and responsibilities" rows={3} />
        </label>
        <div className="modal-note">New agents start at level 1 with 0xp.</div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={close}>
            Cancel
          </button>
          <button className="primary-button" disabled={busy}>
            {busy ? 'Adding agent...' : 'Hire agent'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
