import { Modal } from './Modal'

export function ShortcutHelp({ close }: { close: () => void }) {
  return (
    <Modal title="keyboard shortcuts" subtitle="Shortcuts outside text fields." close={close}>
      <dl className="shortcut-list">
        {[
          ['Ctrl / ⌘ K', 'command palette'],
          ['Alt ↑ / ↓', 'previous / next channel'],
          [']', 'toggle information pane'],
          ['Esc', 'close panes and dialogs'],
          ['?', 'show shortcuts'],
          ['n', 'new task'],
          [',', 'settings'],
          ['h / l', 'move focused task left / right'],
          ['Enter', 'send message'],
          ['Shift Enter', 'new line'],
        ].map(([key, action]) => (
          <div key={key}>
            <dt>
              <kbd>{key}</kbd>
            </dt>
            <dd>{action}</dd>
          </div>
        ))}
      </dl>
    </Modal>
  )
}
