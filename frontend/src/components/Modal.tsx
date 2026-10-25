import { useEffect, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'

export function Modal({
  title,
  subtitle,
  close,
  children,
}: {
  title: string
  subtitle: string
  close: () => void
  children: ReactNode
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    dialog.current?.showModal()
    const el = dialog.current
    return () => el?.close()
  }, [])
  return (
    <dialog
      ref={dialog}
      className="modal"
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close()
      }}
    >
      <div className="modal-inner">
        <button className="modal-close icon-button" onClick={close} aria-label="Close dialog">
          <X size={20} />
        </button>
        <span className="eyebrow">YOUR TEAM, REIMAGINED</span>
        <h2>{title}</h2>
        <p>{subtitle}</p>
        {children}
      </div>
    </dialog>
  )
}
