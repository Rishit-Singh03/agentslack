import { useEffect } from 'react'

export function useShortcuts(actions: {
  palette: () => void
  escape: () => void
  help: () => void
  pane: () => void
  task: () => void
  settings: () => void
  channel: (direction: number) => void
}) {
  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if (event.isComposing) return
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        actions.palette()
        return
      }
      if (event.key === 'Escape') {
        actions.escape()
        return
      }
      if (document.querySelector('dialog[open]')) return
      if (event.altKey && ['ArrowUp', 'ArrowDown'].includes(event.key)) {
        event.preventDefault()
        actions.channel(event.key === 'ArrowDown' ? 1 : -1)
        return
      }
      if (
        event.target instanceof Element &&
        event.target.closest('input, textarea, select, [contenteditable="true"]')
      )
        return
      if (event.ctrlKey || event.metaKey || event.altKey) return
      const action = {
        '?': actions.help,
        ']': actions.pane,
        n: actions.task,
        ',': actions.settings,
      }[event.key]
      if (action) {
        event.preventDefault()
        action()
      }
    }
    window.addEventListener('keydown', handle)
    return () => window.removeEventListener('keydown', handle)
  }, [actions])
}
