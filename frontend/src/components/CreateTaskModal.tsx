import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Agent, Channel, Task } from '../api/types'
import { Modal } from './Modal'

export function CreateTaskModal({
  agents,
  channels,
  close,
  created,
}: {
  agents: Agent[]
  channels: Channel[]
  close: () => void
  created: (t: Task) => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setBusy(true)
    setError('')
    try {
      created(
        await api.createTask({
          title: String(data.get('title')).trim(),
          description: String(data.get('description')).trim(),
          assignee_agent_id: Number(data.get('agent')),
          channel_id: data.get('channel') ? Number(data.get('channel')) : null,
          priority: String(data.get('priority')),
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
      title="new task"
      subtitle="Assign work to an agent and choose a channel for updates."
      close={close}
    >
      <form onSubmit={submit}>
        {!agents.length && (
          <p className="form-error">No agents available. Hire an agent before creating a task.</p>
        )}
        <label>
          Task title
          <input name="title" required maxLength={200} placeholder="Task title" />
        </label>
        <label>
          Description
          <textarea name="description" rows={3} placeholder="Scope and acceptance criteria" />
        </label>
        <div className="form-row">
          <label>
            Assign to
            <select name="agent" required>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Priority
            <select name="priority" defaultValue="med">
              <option value="low">Low</option>
              <option value="med">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
        </div>
        <label>
          Post updates in
          <select name="channel">
            <option value="">No channel</option>
            {channels
              .filter((c) => !c.is_dm)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.name}
                </option>
              ))}
          </select>
        </label>
        <div className="modal-note">Completion awards 25xp once per task.</div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={close}>
            Cancel
          </button>
          <button className="primary-button" disabled={busy || !agents.length}>
            {busy ? 'Creating…' : 'Create task'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
