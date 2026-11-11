import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { apiFetch } from '../../api/client'
import { Dialog, DialogActions } from '../../components/Dialog'
import { ErrorText } from '../../components/QueryState'

/** Invite a parent of this student, or the student themselves when they are adult. */
export function InviteDialog({
  studentId,
  role,
  onClose,
}: {
  studentId: number
  role: 'parent' | 'student'
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const invite = useMutation({
    mutationFn: () =>
      apiFetch('/invitations/', { method: 'POST', body: { email, role, student_ids: [studentId] } }),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    invite.mutate()
  }

  return (
    <Dialog title={t(role === 'parent' ? 'invite.parentTitle' : 'invite.studentTitle')} onClose={onClose}>
      {invite.isSuccess ? (
        <>
          <p role="status" className="ms-alert ms-alert--warning">
            {t('invite.sent', { email })}
          </p>
          <DialogActions>
            <button type="button" className="ms-btn ms-btn--primary" onClick={onClose}>
              {t('invite.done')}
            </button>
          </DialogActions>
        </>
      ) : (
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
          <ErrorText error={invite.error} />
          <DialogActions>
            <button type="button" className="ms-btn ms-btn--secondary" onClick={onClose}>
              {t('lesson.cancel')}
            </button>
            <button type="submit" className="ms-btn ms-btn--primary" disabled={invite.isPending}>
              {t('team.send')}
            </button>
          </DialogActions>
        </form>
      )}
    </Dialog>
  )
}
