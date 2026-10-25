import type { Department } from '../api/types'

export function DepartmentSelect({
  departments,
  value,
}: {
  departments: Department[]
  value?: number | null
}) {
  return (
    <label>
      Department
      <select aria-label="Department" name="department_id" defaultValue={value ?? ''}>
        <option value="">Unassigned</option>
        {departments.map((department) => (
          <option key={department.id} value={department.id}>
            {department.name}
          </option>
        ))}
      </select>
    </label>
  )
}
