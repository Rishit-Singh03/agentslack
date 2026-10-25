import { useCallback, useEffect, useRef, useState } from 'react'
import { Sparkles, X } from 'lucide-react'
import { api } from './api/client'
import type { Agent, Channel, Message, Task, TaskStatus } from './api/types'
import { useSocket } from './hooks/useSocket'
import { Sidebar, type View } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { ChannelView } from './components/ChannelView'
import { AgentProfile } from './components/AgentProfile'
import { AgentDirectory } from './components/AgentDirectory'
import { TaskBoard } from './components/TaskBoard'
import { HireAgentModal } from './components/HireAgentModal'
import { CreateTaskModal } from './components/CreateTaskModal'

function upsert<T extends { id: number }>(items: T[], item: T): T[] {
  return items.some((i) => i.id === item.id)
    ? items.map((i) => (i.id === item.id ? item : i))
    : [...items, item]
}
export default function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [channelId, setChannelId] = useState<number | null>(null)
  const activeId = useRef(channelId)
  activeId.current = channelId
  const [channel, setChannel] = useState<Channel | null>(null)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [view, setView] = useState<View>('channel')
  const [modal, setModal] = useState<'hire' | 'task' | null>(null)
  const [mobile, setMobile] = useState(false)
  const [loading, setLoading] = useState(true)
  const [messageLoading, setMessageLoading] = useState(false)
  const [more, setMore] = useState(false)
  const [error, setError] = useState('')
  const [theme, setTheme] = useState(() => localStorage.getItem('agentslack-theme') || 'dark')
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('agentslack-theme', theme)
  }, [theme])
  const refresh = useCallback(async () => {
    try {
      const [a, c, t] = await Promise.all([api.agents(), api.channels(), api.tasks()])
      setAgents(a)
      setChannels(c)
      setTasks(t)
      setChannelId((current) => current ?? c.find((x) => !x.is_dm)?.id ?? null)
      setError('')
    } catch (e) {
      setError(`Cannot reach your workspace. ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    void refresh()
  }, [refresh])
  const reloadMessages = useCallback(() => {
    const id = activeId.current
    if (id)
      void api
        .messages(id)
        .then((m) => {
          if (activeId.current === id) {
            setMessages((old) =>
              [...new Map([...m, ...old].map((x) => [x.id, x])).values()].sort(
                (a, b) => a.id - b.id,
              ),
            )
          }
        })
        .catch((e) => setError((e as Error).message))
  }, [])
  const connected = useSocket(
    (event) => {
      if (event.type === 'agent.updated') setAgents((old) => upsert(old, event.data))
      if (event.type === 'task.updated') setTasks((old) => upsert(old, event.data))
      if (event.type === 'message.created' && event.data.channel_id === activeId.current)
        setMessages((old) => upsert(old, event.data).sort((a, b) => a.id - b.id))
    },
    () => {
      void refresh()
      reloadMessages()
    },
  )
  useEffect(() => {
    if (!channelId) return
    let alive = true
    setMessageLoading(true)
    setMessages([])
    setChannel(null)
    Promise.all([api.channel(channelId), api.messages(channelId)])
      .then(([c, m]) => {
        if (alive) {
          setChannel(c)
          setMessages((old) =>
            [...new Map([...m, ...old].map((x) => [x.id, x])).values()].sort((a, b) => a.id - b.id),
          )
          setMore(m.length === 50)
        }
      })
      .catch((e) => {
        if (alive) setError((e as Error).message)
      })
      .finally(() => {
        if (alive) setMessageLoading(false)
      })
    return () => {
      alive = false
    }
  }, [channelId])
  const select = (c: Channel) => {
    setChannelId(c.id)
    setView('channel')
    setMobile(false)
  }
  const dm = async (agent: Agent) => {
    try {
      const c = await api.dm(agent.id)
      setChannels((old) => upsert(old, c))
      select(c)
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const move = async (id: number, status: TaskStatus) => {
    try {
      const updated = await api.moveTask(id, status)
      setTasks((old) => upsert(old, updated))
      if (!connected) {
        await refresh()
        reloadMessages()
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const loadMore = async () => {
    if (!channelId || !messages.length) return
    const id = channelId
    try {
      const older = await api.messages(id, messages[0].id)
      if (activeId.current === id) {
        setMessages((old) =>
          [...new Map([...older, ...old].map((x) => [x.id, x])).values()].sort(
            (a, b) => a.id - b.id,
          ),
        )
        setMore(older.length === 50)
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }
  const send = async (body: string) => {
    if (!channelId) return
    const id = channelId
    const m = await api.send(id, body)
    if (activeId.current === id) setMessages((old) => upsert(old, m).sort((a, b) => a.id - b.id))
  }
  const selectedAgent = agents.find((a) => a.id === profileId)
  return (
    <div className="app-shell">
      <TopBar
        agents={agents}
        channels={channels}
        connected={connected}
        theme={theme}
        toggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
        openNavigation={() => setMobile(true)}
        selectChannel={select}
        selectAgent={(agent) => setProfileId(agent.id)}
      />
      <div className="workspace-layout">
        <Sidebar
          agents={agents}
          channels={channels}
          active={channelId}
          view={view}
          open={mobile}
          close={() => setMobile(false)}
          navigate={(v) => {
            setView(v)
            setMobile(false)
          }}
          select={select}
          dm={(a) => void dm(a)}
          hire={() => setModal('hire')}
        />
        <main className="main-panel">
          {error && (
            <div className="error-banner" role="alert">
              {error}
              <button onClick={() => void refresh()}>Retry</button>
              <button onClick={() => setError('')} aria-label="Dismiss error">
                <X size={15} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading-state">
              <Sparkles size={28} />
              Getting your team together…
            </div>
          ) : view === 'channel' ? (
            channel ? (
              <ChannelView
                channel={channel}
                agents={agents}
                messages={messages}
                loading={messageLoading}
                more={more}
                loadMore={() => void loadMore()}
                send={send}
                profile={(a) => setProfileId(a.id)}
              />
            ) : (
              <div className="loading-state">
                {error ? 'Start the backend to connect your workspace.' : 'Opening your workspace…'}
              </div>
            )
          ) : view === 'tasks' ? (
            <TaskBoard
              tasks={tasks}
              agents={agents}
              create={() => setModal('task')}
              move={(id, status) => void move(id, status)}
              profile={(a) => setProfileId(a.id)}
            />
          ) : (
            <AgentDirectory
              agents={agents}
              profile={(a) => setProfileId(a.id)}
              hire={() => setModal('hire')}
            />
          )}
        </main>
        {selectedAgent && (
          <AgentProfile
            agent={selectedAgent}
            tasks={tasks}
            close={() => setProfileId(null)}
            dm={(a) => void dm(a)}
          />
        )}
      </div>
      {modal === 'hire' && (
        <HireAgentModal
          close={() => setModal(null)}
          hired={(a) => {
            setAgents((old) => upsert(old, a))
            setProfileId(a.id)
          }}
        />
      )}
      {modal === 'task' && (
        <CreateTaskModal
          agents={agents}
          channels={channels}
          close={() => setModal(null)}
          created={(t) => setTasks((old) => upsert(old, t))}
        />
      )}
    </div>
  )
}
