import type {
  Agent,
  Channel,
  Department,
  DepartmentDraft,
  DepartmentTemplate,
  MemoryEntry,
  Message,
  Org,
  Task,
  UserProfile,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(
      typeof body.detail === 'string'
        ? body.detail
        : `Request failed (${response.status}). Please check your input.`,
    )
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>)
}
const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })
const patch = (body: unknown): RequestInit => ({ method: 'PATCH', body: JSON.stringify(body) })
export const api = {
  departments: () => request<Department[]>('/departments'),
  departmentCatalog: () => request<DepartmentTemplate[]>('/departments/catalog'),
  createDepartment: (body: DepartmentDraft) => request<Department>('/departments', post(body)),
  updateDepartment: (id: number, body: Partial<DepartmentDraft>) =>
    request<Department>(`/departments/${id}`, patch(body)),
  deleteDepartment: (id: number) => request<void>(`/departments/${id}`, { method: 'DELETE' }),
  org: () => request<Org>('/org'),
  me: () => request<UserProfile>('/me'),
  updateOrg: (body: Partial<Org>) => request<Org>('/org', patch(body)),
  updateMe: (body: Partial<UserProfile>) => request<UserProfile>('/me', patch(body)),
  onboard: (body: {
    name: string
    display_name: string
    handle: string
    accent: string
    sample_team: boolean
    departments?: DepartmentDraft[]
  }) => request<Org>('/onboarding', post(body)),
  createChannel: (body: { name: string; topic: string }) =>
    request<Channel>('/channels', post(body)),
  updateChannel: (id: number, body: { name?: string; topic?: string }) =>
    request<Channel>(`/channels/${id}`, patch(body)),
  deleteChannel: (id: number) => request<void>(`/channels/${id}`, { method: 'DELETE' }),
  updateAgent: (id: number, body: Partial<Agent>) => request<Agent>(`/agents/${id}`, patch(body)),
  deleteAgent: (id: number) => request<void>(`/agents/${id}`, { method: 'DELETE' }),
  agents: () => request<Agent[]>('/agents'),
  channels: () => request<Channel[]>('/channels'),
  channel: (id: number) => request<Channel>(`/channels/${id}`),
  tasks: () => request<Task[]>('/tasks'),
  memory: (id: number) => request<MemoryEntry[]>(`/agents/${id}/memory`),
  messages: (id: number, before?: number) =>
    request<Message[]>(`/channels/${id}/messages?limit=50${before ? `&before=${before}` : ''}`),
  send: (id: number, body: string) => request<Message>(`/channels/${id}/messages`, post({ body })),
  dm: (id: number) => request<Channel>(`/dms/${id}`, post({})),
  hire: (body: {
    name: string
    handle: string
    department_id: number | null
    title: string
    bio: string
    skills: string[]
  }) => request<Agent>('/agents', post(body)),
  createTask: (body: {
    title: string
    description: string
    assignee_agent_id: number
    channel_id: number | null
    priority: string
  }) => request<Task>('/tasks', post(body)),
  moveTask: (id: number, status: string) =>
    request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
}
