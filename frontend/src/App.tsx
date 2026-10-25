import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import type { Agent, Channel, Org, TaskStatus, View } from './api/types'
import { useWorkspace } from './hooks/useWorkspace'
import { useShortcuts } from './hooks/useShortcuts'
import { upsert } from './utils'
import { TopBar } from './components/TopBar'
import { Sidebar } from './components/Sidebar'
import { StatusLine } from './components/StatusLine'
import { ChannelView } from './components/ChannelView'
import { TaskBoard } from './components/TaskBoard'
import { AgentDirectory } from './components/AgentDirectory'
import { AgentProfile } from './components/AgentProfile'
import { ChannelInfo } from './components/ChannelInfo'
import { ActivityFeed } from './components/ActivityFeed'
import { SettingsView } from './components/SettingsView'
import { Onboarding } from './components/Onboarding'
import { CommandPalette, type Command } from './components/CommandPalette'
import { ShortcutHelp } from './components/ShortcutHelp'
import { HireAgentModal } from './components/HireAgentModal'
import { CreateTaskModal } from './components/CreateTaskModal'
import { CreateChannelModal } from './components/CreateChannelModal'

export default function App() {
  const workspace = useWorkspace()
  const [view, setView] = useState<View>(() =>
    location.pathname === '/settings' ? 'settings' : 'channel',
  )
  const [profileId, setProfileId] = useState<number | null>(null)
  const [channelInfo, setChannelInfo] = useState(false)
  const [modal, setModal] = useState<'hire' | 'task' | 'channel' | 'help' | null>(null)
  const [palette, setPalette] = useState(false)
  const [mobile, setMobile] = useState(false)
  const [mode, setMode] = useState<'NORMAL' | 'INSERT'>('NORMAL')
  const [preview, setPreview] = useState<Org | null>(null)
  const appearance = preview ?? workspace.org
  const previewSettings = useCallback((org: Org | null) => setPreview(org), [])
  useEffect(() => {
    if (!appearance) return
    const root = document.documentElement
    root.dataset.theme = appearance.theme
    root.dataset.density = appearance.density
    root.dataset.font = appearance.font_mode
    root.style.setProperty('--accent-user', appearance.accent)
  }, [appearance])
  useEffect(() => {
    const pop = () => setView(location.pathname === '/settings' ? 'settings' : 'channel')
    window.addEventListener('popstate', pop)
    return () => window.removeEventListener('popstate', pop)
  }, [])
  const navigate = (next: View) => {
    setView(next)
    setMobile(false)
    const path = next === 'settings' ? '/settings' : '/'
    if (location.pathname !== path) history.pushState(null, '', path)
  }
  const select = (channel: Channel) => {
    workspace.setChannelId(channel.id)
    navigate('channel')
    setChannelInfo(false)
  }
  const profile = (agent: Agent) => {
    setProfileId(agent.id)
    setChannelInfo(false)
  }
  const report = (error: unknown) => workspace.setError((error as Error).message)
  const dm = async (agent: Agent) => {
    try {
      const channel = await api.dm(agent.id)
      workspace.updateChannel(channel)
      select(channel)
    } catch (error) {
      report(error)
    }
  }
  const togglePane = () => {
    if (profileId !== null || channelInfo) {
      setProfileId(null)
      setChannelInfo(false)
    } else if (workspace.channel?.is_dm) setProfileId(workspace.channel.dm_agent_id)
    else setChannelInfo(true)
  }
  useShortcuts({
    palette: () => setPalette((open) => !open),
    escape: () => {
      setPalette(false)
      setModal(null)
      setProfileId(null)
      setChannelInfo(false)
      setMobile(false)
    },
    help: () => setModal('help'),
    pane: togglePane,
    task: () => setModal('task'),
    settings: () => navigate('settings'),
    channel: (direction) => {
      const rooms = workspace.channels.filter((channel) => !channel.is_dm)
      const index = rooms.findIndex((channel) => channel.id === workspace.channelId)
      if (rooms.length) select(rooms[(index + direction + rooms.length) % rooms.length])
    },
  })
  const toggleTheme = async () => {
    if (!workspace.org) return
    try {
      workspace.setOrg(
        await api.updateOrg({ theme: workspace.org.theme === 'dark' ? 'paper' : 'dark' }),
      )
    } catch (error) {
      report(error)
    }
  }
  const move = async (id: number, status: TaskStatus) => {
    try {
      const updated = await api.moveTask(id, status)
      workspace.setTasks((tasks) => upsert(tasks, updated))
      if (!workspace.connected) {
        await workspace.refresh()
        workspace.reloadMessages()
      }
    } catch (error) {
      report(error)
    }
  }
  const send = async (body: string) => {
    const id = workspace.channelId
    if (!id) throw new Error('Select a channel first')
    if (body === '/clear') {
      workspace.setMessages([])
      workspace.log('local conversation view cleared')
      return
    }
    if (body === '/hire') {
      setModal('hire')
      return
    }
    if (body === '/settings') {
      navigate('settings')
      return
    }
    if (body.startsWith('/topic ')) {
      workspace.updateChannel(await api.updateChannel(id, { topic: body.slice(7).trim() }))
      return
    }
    if (body.startsWith('/task ')) {
      const match = body.match(/^\/task\s+(.+?)\s+(@[a-z][a-z0-9_]*)$/i)
      const assignee = workspace.agents.find((agent) => agent.handle === match?.[2].toLowerCase())
      if (!match || !assignee) throw new Error('Usage: /task <title> @agent')
      const task = await api.createTask({
        title: match[1],
        description: '',
        assignee_agent_id: assignee.id,
        channel_id: id,
        priority: 'med',
      })
      workspace.setTasks((tasks) => upsert(tasks, task))
      return
    }
    if (body.startsWith('/'))
      throw new Error('Unknown command. Use /task, /topic, /hire, or /clear.')
    const message = await api.send(id, body)
    if (workspace.channelId === id)
      workspace.setMessages((messages) => upsert(messages, message).sort((a, b) => a.id - b.id))
  }
  const commands: Command[] = [
    ...workspace.channels
      .filter((channel) => !channel.is_dm)
      .map((channel) => ({
        id: `channel-${channel.id}`,
        label: `#${channel.name}`,
        category: 'channel',
        run: () => select(channel),
      })),
    ...workspace.agents.map((agent) => ({
      id: `agent-${agent.id}`,
      label: `${agent.handle} ${agent.title}`,
      category: 'agent',
      run: () => profile(agent),
    })),
    { id: 'task', label: 'new task', category: 'action', run: () => setModal('task') },
    { id: 'hire', label: 'hire agent', category: 'action', run: () => setModal('hire') },
    { id: 'new-channel', label: 'new channel', category: 'action', run: () => setModal('channel') },
    ...(['tasks', 'agents', 'activity', 'settings'] as const).map((next) => ({
      id: next,
      label: next,
      category: 'view',
      run: () => navigate(next),
    })),
    { id: 'theme', label: 'toggle theme', category: 'action', run: () => void toggleTheme() },
    { id: 'help', label: 'keyboard shortcuts', category: 'help', run: () => setModal('help') },
  ]
  if (workspace.loading)
    return (
      <div className="boot-screen">
        $ agentslack attach
        <br />
        <span className="dim">connecting...</span>
      </div>
    )
  if (!workspace.org || !workspace.me)
    return (
      <div className="boot-screen" role="alert">
        {workspace.error || 'Cannot load workspace.'}
        <button onClick={() => void workspace.refresh()}>[retry]</button>
      </div>
    )
  if (!workspace.org.initialized) return <Onboarding initialized={workspace.refresh} />
  const org = workspace.org
  const me = workspace.me
  const selectedAgent = workspace.agents.find((agent) => agent.id === profileId)
  const renderView = () => {
    switch (view) {
      case 'settings':
        return (
          <SettingsView
            departments={workspace.departments}
            org={org}
            me={me}
            departmentChanged={(department) =>
              workspace.setDepartments((current) =>
                upsert(current, department).sort(
                  (a, b) => a.sort_order - b.sort_order || a.id - b.id,
                ),
              )
            }
            departmentRemoved={(id) => {
              workspace.setDepartments((current) => current.filter((item) => item.id !== id))
              void workspace.refresh()
            }}
            preview={previewSettings}
            saved={(updated, profile) => {
              workspace.setOrg(updated)
              workspace.setMe(profile)
            }}
          />
        )
      case 'tasks':
        return (
          <TaskBoard
            departments={workspace.departments}
            tasks={workspace.tasks}
            agents={workspace.agents}
            create={() => setModal('task')}
            move={(id, status) => void move(id, status)}
            profile={profile}
          />
        )
      case 'agents':
        return (
          <AgentDirectory
            departments={workspace.departments}
            agents={workspace.agents}
            profile={profile}
            hire={() => setModal('hire')}
          />
        )
      case 'activity':
        return <ActivityFeed entries={workspace.activity} />
      case 'channel':
        return workspace.channel ? (
          <ChannelView
            departments={workspace.departments}
            channel={workspace.channel}
            agents={workspace.agents}
            messages={workspace.messages}
            loading={workspace.messageLoading}
            more={workspace.more}
            loadMore={() => void workspace.loadMore()}
            send={send}
            profile={profile}
            info={togglePane}
            me={me}
            flashes={workspace.flashes}
            onMode={setMode}
          />
        ) : (
          <p className="empty-state">Select a channel or create one from the sidebar.</p>
        )
    }
  }
  return (
    <div className="app-shell">
      <TopBar
        org={org}
        me={me}
        connected={workspace.connected}
        palette={() => setPalette(true)}
        settings={() => navigate('settings')}
        openNavigation={() => setMobile(true)}
      />
      <div className="workspace-layout">
        <Sidebar
          departments={workspace.departments}
          org={org}
          flashes={workspace.flashes}
          agents={workspace.agents}
          channels={workspace.channels}
          active={workspace.channelId}
          view={view}
          open={mobile}
          close={() => setMobile(false)}
          navigate={navigate}
          select={select}
          dm={(agent) => void dm(agent)}
          hire={() => setModal('hire')}
          newChannel={() => setModal('channel')}
        />
        <main className="main-panel">
          {workspace.error && (
            <div className="error-banner" role="alert">
              {workspace.error}
              <button onClick={() => workspace.setError('')}>[dismiss]</button>
            </div>
          )}
          {renderView()}
        </main>
        {selectedAgent && (
          <AgentProfile
            departments={workspace.departments}
            agent={selectedAgent}
            tasks={workspace.tasks}
            close={() => setProfileId(null)}
            dm={(agent) => void dm(agent)}
            changed={(agent) => workspace.setAgents((agents) => upsert(agents, agent))}
            dismissed={(id) =>
              workspace.setAgents((agents) => agents.filter((agent) => agent.id !== id))
            }
          />
        )}
        {!selectedAgent && channelInfo && workspace.channel && (
          <ChannelInfo
            key={workspace.channel.id}
            channel={workspace.channel}
            close={() => setChannelInfo(false)}
            changed={workspace.updateChannel}
            removed={workspace.removeChannel}
          />
        )}
      </div>
      <StatusLine
        mode={mode}
        org={org}
        view={view === 'channel' ? `#${workspace.channel?.name ?? '-'}` : view}
        agents={workspace.agents}
        tasks={workspace.tasks}
        connected={workspace.connected}
      />
      {palette && <CommandPalette commands={commands} close={() => setPalette(false)} />}
      {modal === 'help' && <ShortcutHelp close={() => setModal(null)} />}
      {modal === 'hire' && (
        <HireAgentModal
          departments={workspace.departments}
          close={() => setModal(null)}
          hired={(agent) => {
            workspace.setAgents((agents) => upsert(agents, agent))
            profile(agent)
          }}
        />
      )}
      {modal === 'task' && (
        <CreateTaskModal
          agents={workspace.agents}
          channels={workspace.channels}
          close={() => setModal(null)}
          created={(task) => workspace.setTasks((tasks) => upsert(tasks, task))}
        />
      )}
      {modal === 'channel' && (
        <CreateChannelModal
          close={() => setModal(null)}
          created={(channel) => {
            workspace.updateChannel(channel)
            select(channel)
          }}
        />
      )}
      {appearance?.crt_effects && (
        <div className="crt-overlay" aria-hidden="true">
          {Array.from({ length: 600 }, (_, index) => (
            <i key={index} />
          ))}
        </div>
      )}
    </div>
  )
}
