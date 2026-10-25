import type { Agent, Channel, MemoryEntry, Message, Task } from './types'

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
  return response.json() as Promise<T>
}
const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) })
export const api = {
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
    role: string
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
