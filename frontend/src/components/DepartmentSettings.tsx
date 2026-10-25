import { useState } from 'react'
import { api } from '../api/client'
import type { Department } from '../api/types'
import { DepartmentEditor } from './DepartmentEditor'
import { departmentStyle } from './DepartmentTag'

export function DepartmentSettings({
  departments,
  changed,
  removed,
}: {
  departments: Department[]
  changed: (department: Department) => void
  removed: (id: number) => void
}) {
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  const [confirm, setConfirm] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const move = async (index: number, direction: number) => {
    const ordered = [...departments]
    ;[ordered[index], ordered[index + direction]] = [ordered[index + direction], ordered[index]]
    setBusy(true)
    setError('')
    try {
      for (const [position, department] of ordered.entries()) {
        if (department.sort_order !== position)
          changed(await api.updateDepartment(department.id, { sort_order: position }))
      }
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const remove = async (id: number) => {
    setBusy(true)
    setError('')
    try {
      await api.deleteDepartment(id)
      removed(id)
      setConfirm(null)
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="settings-section department-settings" aria-label="Departments settings">
      <div className="section-heading">
        <h2>DEPARTMENTS ({departments.length})</h2>
        <button onClick={() => setEditing('new')}>[+ add department]</button>
      </div>
      <p className="dim">Each department owns a channel. Changes are saved immediately.</p>
      <div className="department-settings-list">
        {departments.map((department, index) => (
          <div className="department-setting" key={department.id}>
            <div className="department-setting-row">
              <span className="department-marker" style={departmentStyle(department)} />
              <div>
                <strong>{department.name}</strong>
                <small>#{department.slug}</small>
              </div>
              <div className="department-controls">
                <button
                  disabled={busy || index === 0}
                  aria-label={`Move ${department.name} up`}
                  onClick={() => void move(index, -1)}
                >
                  [↑]
                </button>
                <button
                  disabled={busy || index === departments.length - 1}
                  aria-label={`Move ${department.name} down`}
                  onClick={() => void move(index, 1)}
                >
                  [↓]
                </button>
                <button
                  onClick={() => setEditing(department.id)}
                  aria-label={`Edit ${department.name}`}
                >
                  [edit]
                </button>
                <button
                  className="danger"
                  onClick={() => setConfirm(department.id)}
                  aria-label={`Remove ${department.name}`}
                >
                  [remove]
                </button>
              </div>
            </div>
            {editing === department.id && (
              <DepartmentEditor
                initial={department}
                cancel={() => setEditing(null)}
                submit={async (draft) => {
                  changed(await api.updateDepartment(department.id, draft))
                  setEditing(null)
                }}
              />
            )}
            {confirm === department.id && (
              <div className="department-confirm">
                <p>
                  Remove {department.name}? Agents become unassigned. Its channel and messages are
                  deleted; tasks remain.
                </p>
                <button
                  className="danger"
                  disabled={busy}
                  onClick={() => void remove(department.id)}
                >
                  [confirm remove]
                </button>
                <button onClick={() => setConfirm(null)}>[cancel]</button>
              </div>
            )}
          </div>
        ))}
      </div>
      {editing === 'new' && (
        <DepartmentEditor
          cancel={() => setEditing(null)}
          submit={async (draft) => {
            changed(
              await api.createDepartment({
                ...draft,
                sort_order: Math.max(-1, ...departments.map((item) => item.sort_order)) + 1,
              }),
            )
            setEditing(null)
          }}
        />
      )}
      {!departments.length && (
        <p className="empty-state">No departments. Add one to organize agents and work.</p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
