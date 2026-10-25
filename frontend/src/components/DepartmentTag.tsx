import type { CSSProperties } from 'react'
import type { Department } from '../api/types'

export function departmentStyle(department?: Department): CSSProperties {
  return department ? ({ '--department-color': department.color } as CSSProperties) : {}
}

export function DepartmentTag({ department }: { department?: Department }) {
  return (
    <span className="department-tag" style={departmentStyle(department)}>
      [{department?.name ?? 'unassigned'}]
    </span>
  )
}
