import type { ReactNode } from 'react'

import { Logo } from '../components/ui'

/** The shell of the public account pages (register, confirm, reset, invitation). */
export function AuthLayout({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div className="login-page">
      <section className="login-form-side">
        <div className="ms-stack" style={{ gap: 20, width: '100%', maxWidth: 420 }}>
          <Logo size={40} />
          <div className="ms-stack" style={{ gap: 6 }}>
            <h1 style={{ fontSize: 32, fontWeight: 800 }}>{title}</h1>
            {hint && (
              <p className="ms-help" style={{ margin: 0, fontSize: 16 }}>
                {hint}
              </p>
            )}
          </div>
          {children}
        </div>
      </section>
    </div>
  )
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="ms-alert ms-alert--error" style={{ margin: 0 }}>
      <span>{message}</span>
    </p>
  )
}

export function FormNotice({ message }: { message: string }) {
  return (
    <p role="status" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
      <span>{message}</span>
    </p>
  )
}
