import { useEffect, useId, useRef, type ReactNode } from 'react'

/**
 * Centred dialog over a scrim (design/system: Dialog). Escape and a click on the scrim close it;
 * focus goes to the first field when it opens. `children` are the fields and the actions.
 */
export function Dialog({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string
  subtitle?: string
  onClose: () => void
  children: ReactNode
}) {
  const titleId = useId()
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    box.current?.querySelector<HTMLElement>('input, textarea, select, button')?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="ms-modal" onClick={onClose}>
      <div
        ref={box}
        className="ms-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ms-stack" style={{ gap: 4 }}>
          <h2 id={titleId} className="ms-overlay-title">
            {title}
          </h2>
          {subtitle && <span className="ms-overlay-sub">{subtitle}</span>}
        </div>
        {children}
      </div>
    </div>
  )
}

/** Cancel + confirm row at the bottom of a dialog. */
export function DialogActions({ children }: { children: ReactNode }) {
  return (
    <div className="row-between" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
      {children}
    </div>
  )
}
