import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { apiFetch, fetchAllPages } from '../../api/client'
import type { components } from '../../api/schema'
import { AppShell } from '../../components/AppShell'
import { ErrorText, QueryState } from '../../components/QueryState'
import { formatDay } from '../../lib/dates'

type Invitation = components['schemas']['Invitation']
type Teacher = components['schemas']['Teacher']
type Role = 'teacher' | 'parent'

/** The studio owner's team: teachers, and invitations waiting for an answer. */
export function TeamPage() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const teachers = useQuery({
    queryKey: ['teachers'],
    queryFn: () => fetchAllPages<Teacher>('/studio/teachers/'),
  })
  const invitations = useQuery({
    queryKey: ['invitations'],
    queryFn: () => fetchAllPages<Invitation>('/invitations/'),
  })
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<Role>('teacher')
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['invitations'] })

  const invite = useMutation({
    mutationFn: () => apiFetch('/invitations/', { method: 'POST', body: { email, role } }),
    onSuccess: () => {
      setEmail('')
      void refresh()
    },
  })
  const revoke = useMutation({
    mutationFn: (id: number) => apiFetch(`/invitations/${id}/revoke/`, { method: 'POST' }),
    onSuccess: refresh,
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    invite.mutate()
  }

  return (
    <AppShell>
      <div className="page-head__text">
        <h1 className="page-title">{t('nav.team')}</h1>
      </div>

      <section className="panel">
        <h2 className="section-title">{t('team.teachers')}</h2>
        <QueryState query={teachers}>
          <ul className="ms-stack" style={{ listStyle: 'none', padding: 0 }}>
            {teachers.data?.map((teacher) => (
              <li key={teacher.id} className="list-line">
                <span className="list-line__main">{teacher.email}</span>
                {teacher.is_owner && <span className="muted">{t('auth.role.studio_owner')}</span>}
              </li>
            ))}
          </ul>
        </QueryState>
      </section>

      <section className="panel">
        <h2 className="section-title">{t('team.invite')}</h2>
        <form className="ms-form" onSubmit={submit}>
          <label className="ms-field">
            {t('auth.email')}
            <input
              className="ms-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="ms-field">
            {t('team.role')}
            <select className="ms-input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="teacher">{t('auth.role.teacher')}</option>
              <option value="parent">{t('auth.role.parent')}</option>
            </select>
          </label>
          {role === 'parent' && <p className="ms-help">{t('team.parentHint')}</p>}
          <ErrorText error={invite.error} />
          <button type="submit" className="ms-btn ms-btn--primary" disabled={invite.isPending}>
            {t('team.send')}
          </button>
        </form>
      </section>

      <section className="panel">
        <h2 className="section-title">{t('team.pending')}</h2>
        <QueryState
          query={invitations}
          isEmpty={invitations.data?.length === 0}
          emptyText={t('team.noInvitations')}
        >
          <ul className="ms-stack" style={{ listStyle: 'none', padding: 0 }}>
            {invitations.data?.map((inv) => (
              <li key={inv.id} className="list-line">
                <span className="list-line__main">
                  <strong>{inv.email}</strong>
                  <span className="muted">
                    {t(`auth.role.${inv.role}`)} · {t(`team.status.${inv.status}`, inv.status)} ·{' '}
                    {formatDay(inv.expires_at, i18n.language)}
                  </span>
                </span>
                {inv.status === 'pending' && (
                  <button
                    type="button"
                    className="ms-btn ms-btn--secondary"
                    onClick={() => revoke.mutate(inv.id)}
                  >
                    {t('team.revoke')}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </QueryState>
        <ErrorText error={revoke.error} />
      </section>
    </AppShell>
  )
}
