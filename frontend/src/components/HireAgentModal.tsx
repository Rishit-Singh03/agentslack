import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { Agent, Role } from '../api/types'
import { Modal } from './Modal'

export function HireAgentModal({ close, hired }: { close: () => void; hired: (a: Agent) => void }) {
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
          role: String(data.get('role')) as Role,
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
      title="Meet your next teammate."
      subtitle="A little more expertise. A whole lot of possibility."
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
          <label>
            Specialty
            <select name="role">
              {['frontend', 'backend', 'finance', 'design', 'research', 'ops'].map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input name="title" required maxLength={150} placeholder="e.g. Frontend engineer" />
          </label>
        </div>
        <label>
          Skills <span>(comma separated)</span>
          <input name="skills" placeholder="React, TypeScript, Accessibility" />
        </label>
        <label>
          A little about them
          <textarea name="bio" placeholder="What makes this teammate great?" rows={3} />
        </label>
        <div className="modal-note">✧ New agents start at Level 1 with a stub runtime.</div>
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
            {busy ? 'Adding teammate…' : 'Welcome to the team'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
