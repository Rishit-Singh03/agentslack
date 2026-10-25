import { useState, type FormEvent } from 'react'
import type { DepartmentDraft } from '../api/types'

export function DepartmentEditor({
  initial,
  submit,
  cancel,
}: {
  initial?: DepartmentDraft
  submit: (draft: DepartmentDraft) => Promise<void>
  cancel: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      await submit({
        name: String(fields.get('department_name')).trim(),
        description: String(fields.get('description')).trim(),
        color: String(fields.get('department_color')),
        sort_order: initial?.sort_order ?? 0,
      })
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <form className="department-editor" onSubmit={save}>
      <div className="form-row">
        <label>
          Department name
          <input
            name="department_name"
            defaultValue={initial?.name}
            required
            maxLength={80}
            autoFocus
          />
        </label>
        <label>
          Department color
          <input
            name="department_color"
            defaultValue={initial?.color ?? '#3ddc84'}
            required
            pattern="#[0-9a-fA-F]{6}"
          />
        </label>
      </div>
      <label>
        Description
        <textarea name="description" defaultValue={initial?.description} rows={2} maxLength={500} />
      </label>
      <p className="dim">
        A channel is created from the name. Use neutral, green, amber, cyan, blue, or warm colors.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="pane-actions">
        <button className="primary-button" disabled={busy}>
          {initial ? 'Save department' : 'Add department'}
        </button>
        <button type="button" onClick={cancel}>
          [cancel]
        </button>
      </div>
    </form>
  )
}
