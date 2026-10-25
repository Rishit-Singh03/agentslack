export interface Department {
  id: number
  name: string
  slug: string
  description: string
  color: string
  channel_id: number
  sort_order: number
  created_at: string
}
export interface DepartmentDraft {
  name: string
  slug?: string
  description: string
  color: string
  sort_order: number
}
export interface DepartmentTemplate extends Omit<DepartmentDraft, 'sort_order'> {
  slug: string
  core: boolean
}
export interface Agent {
  id: number
  handle: string
  name: string
  department_id: number | null
  title: string
  avatar_color: string
  status: 'online' | 'busy' | 'idle' | 'offline'
  level: number
  xp: number
  skills: string[]
  bio: string
  runtime: string
  created_at: string
}
export interface Channel {
  id: number
  name: string
  topic: string
  is_dm: boolean
  dm_agent_id: number | null
  member_ids?: number[]
}
export interface Message {
  id: number
  channel_id: number
  author_type: 'human' | 'agent' | 'system'
  author_id: number | null
  body: string
  is_streaming: boolean
  thread_parent_id: number | null
  created_at: string
}
export type TaskStatus = 'todo' | 'in_progress' | 'review' | 'done'
export interface Task {
  id: number
  title: string
  description: string
  assignee_agent_id: number
  channel_id: number | null
  status: TaskStatus
  priority: 'low' | 'med' | 'high'
  xp_reward: number
  xp_awarded: boolean
}
export interface MemoryEntry {
  id: number
  kind: string
  content: string
}
export type LiveEvent =
  | { type: 'message.created'; data: Message }
  | { type: 'agent.updated'; data: Agent }
  | { type: 'task.updated'; data: Task }
  | { type: 'message.delta'; data: { id: number; channel_id: number; delta: string } }
  | { type: 'org.updated'; data: Org }
  | { type: 'profile.updated'; data: UserProfile }
  | { type: 'channel.updated'; data: Channel }
  | { type: 'department.updated'; data: Department }
  | { type: 'department.deleted'; data: { id: number } }
  | { type: 'channel.deleted' | 'agent.deleted' | 'task.deleted'; data: { id: number } }

export interface Org {
  id: number
  name: string
  slug: string
  tagline: string
  accent: string
  theme: 'dark' | 'paper'
  density: 'compact' | 'comfortable'
  font_mode: 'mixed' | 'mono'
  crt_effects: boolean
  initialized: boolean
}
export interface UserProfile {
  id: number
  display_name: string
  handle: string
}
export interface Activity {
  id: number
  time: string
  text: string
}
export type View = 'channel' | 'tasks' | 'agents' | 'activity' | 'settings'
