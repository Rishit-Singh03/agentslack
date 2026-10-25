import { useState } from 'react'
import type { DepartmentDraft, DepartmentTemplate } from '../api/types'
import { DepartmentEditor } from './DepartmentEditor'

export function DepartmentChooser({
  catalog,
  selected,
  change,
}: {
  catalog: DepartmentTemplate[]
  selected: DepartmentDraft[]
  change: (selected: DepartmentDraft[]) => void
}) {
  const [custom, setCustom] = useState(false)
  const known = new Set(catalog.map((item) => item.name))
  const [customDepartments, setCustomDepartments] = useState<DepartmentDraft[]>(() =>
    selected.filter((item) => !known.has(item.name)),
  )
  const options = [...catalog, ...customDepartments]
  return (
    <div className="department-chooser">
      <p className="dim">
        Core departments are selected by default. Each selected department gets its own channel.
      </p>
      <div className="department-options">
        {options.map((item) => (
          <label className="department-option" key={item.name}>
            <input
              type="checkbox"
              checked={selected.some((department) => department.name === item.name)}
              onChange={(event) =>
                change(
                  event.target.checked
                    ? [
                        ...selected,
                        {
                          name: item.name,
                          slug: item.slug,
                          description: item.description,
                          color: item.color,
                          sort_order: selected.length,
                        },
                      ]
                    : selected.filter((department) => department.name !== item.name),
                )
              }
            />
            <span>
              <strong>{item.name}</strong>
              <small>{item.description}</small>
            </span>
          </label>
        ))}
      </div>
      {custom ? (
        <DepartmentEditor
          cancel={() => setCustom(false)}
          submit={async (draft) => {
            if (options.some((item) => item.name.toLowerCase() === draft.name.toLowerCase()))
              throw new Error('Department already selected')
            setCustomDepartments((current) => [...current, draft])
            change([...selected, { ...draft, sort_order: selected.length }])
            setCustom(false)
          }}
        />
      ) : (
        <button className="secondary-button" onClick={() => setCustom(true)}>
          + add custom department
        </button>
      )}
      <p className="dim selection-count">
        {selected.length} departments selected. You can edit them later in settings.
      </p>
    </div>
  )
}
