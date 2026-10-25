export type Role = 'frontend' | 'backend' | 'finance' | 'design' | 'research' | 'ops'
export interface Agent {
  id: number
  handle: string
  name: string
  role: Role
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
