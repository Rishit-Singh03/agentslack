import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type {
  Activity,
  Agent,
  Channel,
  Department,
  Message,
  Org,
  Task,
  UserProfile,
} from '../api/types'
import { mergeMessages, upsert } from '../utils'
import { useSocket } from './useSocket'

export function useWorkspace() {
  const [org, setOrg] = useState<Org | null>(null)
  const [me, setMe] = useState<UserProfile | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [channels, setChannels] = useState<Channel[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [channelId, setChannelId] = useState<number | null>(null)
  const [channel, setChannel] = useState<Channel | null>(null)
  const [loading, setLoading] = useState(true)
  const [messageLoading, setMessageLoading] = useState(false)
  const [more, setMore] = useState(false)
  const [error, setError] = useState('')
  const [activity, setActivity] = useState<Activity[]>([])
  const [flashes, setFlashes] = useState<number[]>([])
  const activeId = useRef(channelId)
  activeId.current = channelId
  const flashTimers = useRef<ReturnType<typeof setTimeout>[]>([])
  useEffect(() => () => flashTimers.current.forEach(clearTimeout), [])

  const log = useCallback((text: string) => {
    setActivity((entries) =>
      [
        ...entries,
        { id: (entries.at(-1)?.id ?? 0) + 1, time: new Date().toISOString(), text },
      ].slice(-500),
    )
  }, [])
  const refresh = useCallback(async () => {
    try {
      const [loadedOrg, profile, people, rooms, work, teams] = await Promise.all([
        api.org(),
        api.me(),
        api.agents(),
        api.channels(),
        api.tasks(),
        api.departments(),
      ])
      setOrg(loadedOrg)
      setMe(profile)
      setAgents(people)
      setChannels(rooms)
      setTasks(work)
      setDepartments(teams)
      setChannelId((current) =>
        rooms.some((room) => room.id === current)
          ? current
          : (rooms.find((room) => !room.is_dm)?.id ?? null),
      )
      setError('')
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    void refresh()
  }, [refresh])

  const updateChannel = useCallback((updated: Channel) => {
    setChannels((rooms) => upsert(rooms, updated))
    setChannel((current) => (current?.id === updated.id ? { ...current, ...updated } : current))
  }, [])
  const removeChannel = useCallback((id: number) => {
    setChannels((rooms) => rooms.filter((room) => room.id !== id))
    setTasks((work) =>
      work.map((task) => (task.channel_id === id ? { ...task, channel_id: null } : task)),
    )
    setChannelId((current) => (current === id ? null : current))
  }, [])
  useEffect(() => {
    if (channelId === null && channels.length)
      setChannelId(channels.find((room) => !room.is_dm)?.id ?? null)
  }, [channelId, channels])

  const reloadMessages = useCallback(() => {
    const id = activeId.current
    if (id)
      void api
        .messages(id)
        .then((loaded) => {
          if (activeId.current === id) {
            setMessages(loaded)
            setMore(loaded.length === 50)
          }
        })
        .catch((error) => setError((error as Error).message))
  }, [])
  const connected = useSocket(
    (event) => {
      switch (event.type) {
        case 'department.updated':
          setDepartments((current) =>
            upsert(current, event.data).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id),
          )
          log(`department ${event.data.name} updated`)
          break
        case 'department.deleted':
          setDepartments((current) =>
            current.filter((department) => department.id !== event.data.id),
          )
          log(`department #${event.data.id} removed`)
          break
        case 'org.updated':
          setOrg(event.data)
          log('org settings updated')
          void refresh()
          break
        case 'profile.updated':
          setMe(event.data)
          log(`profile ${event.data.handle} updated`)
          break
        case 'agent.updated': {
          const previous = agents.find((agent) => agent.id === event.data.id)
          if (previous?.status !== event.data.status)
            log(`${event.data.handle} status ${previous?.status ?? 'new'} → ${event.data.status}`)
          if (previous && event.data.level > previous.level) {
            log(
              `${event.data.handle} lvl ${previous.level} → ${event.data.level} (+${event.data.xp - previous.xp}xp)`,
            )
            setFlashes((ids) => [...ids, event.data.id])
            flashTimers.current.push(
              setTimeout(() => setFlashes((ids) => ids.filter((id) => id !== event.data.id)), 1400),
            )
          }
          setAgents((people) => upsert(people, event.data))
          break
        }
        case 'channel.updated':
          updateChannel(event.data)
          log(`#${event.data.name} updated`)
          break
        case 'channel.deleted':
          removeChannel(event.data.id)
          log(`channel #${event.data.id} deleted`)
          break
        case 'agent.deleted':
          setAgents((people) => people.filter((agent) => agent.id !== event.data.id))
          log(`agent #${event.data.id} dismissed`)
          break
        case 'task.deleted':
          setTasks((work) => work.filter((task) => task.id !== event.data.id))
          break
        case 'task.updated': {
          const previous = tasks.find((task) => task.id === event.data.id)
          if (previous?.status !== event.data.status)
            log(
              `task #${event.data.id} ${previous?.status ?? 'new'} → ${event.data.status}${event.data.status === 'done' && previous && !previous.xp_awarded ? ` (+${event.data.xp_reward}xp)` : ''}`,
            )
          setTasks((work) => upsert(work, event.data))
          break
        }
        case 'message.created':
          if (event.data.channel_id === activeId.current)
            setMessages((current) => upsert(current, event.data).sort((a, b) => a.id - b.id))
          if (!event.data.is_streaming)
            log(
              `message #${event.data.id} ${event.data.author_type} → channel #${event.data.channel_id}`,
            )
          break
        case 'message.delta':
          if (event.data.channel_id === activeId.current)
            setMessages((current) =>
              current.map((message) =>
                message.id === event.data.id
                  ? { ...message, body: message.body + event.data.delta }
                  : message,
              ),
            )
          break
      }
    },
    () => {
      void refresh()
      reloadMessages()
    },
  )

  useEffect(() => {
    if (!channelId) {
      setChannel(null)
      setMessages([])
      return
    }
    let alive = true
    setMessageLoading(true)
    setChannel(null)
    setMessages([])
    Promise.all([api.channel(channelId), api.messages(channelId)])
      .then(([room, loaded]) => {
        if (!alive) return
        setChannel(room)
        setMessages((current) =>
          mergeMessages(
            loaded,
            current.filter((message) => message.channel_id === channelId),
          ),
        )
        setMore(loaded.length === 50)
      })
      .catch((error) => {
        if (alive) setError((error as Error).message)
      })
      .finally(() => {
        if (alive) setMessageLoading(false)
      })
    return () => {
      alive = false
    }
  }, [channelId])

  const loadMore = async () => {
    if (!channelId || !messages.length) return
    const id = channelId
    try {
      const older = await api.messages(id, messages[0].id)
      if (activeId.current === id) {
        setMessages((current) => mergeMessages(older, current))
        setMore(older.length === 50)
      }
    } catch (error) {
      setError((error as Error).message)
    }
  }

  return {
    org,
    setOrg,
    me,
    setMe,
    agents,
    departments,
    setDepartments,
    setAgents,
    channels,
    setChannels,
    tasks,
    setTasks,
    messages,
    setMessages,
    channelId,
    setChannelId,
    channel,
    loading,
    messageLoading,
    more,
    error,
    setError,
    activity,
    flashes,
    log,
    refresh,
    reloadMessages,
    updateChannel,
    removeChannel,
    loadMore,
    connected,
  }
}
