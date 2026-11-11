// The owner's team page and the invite buttons on a student (US3).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { page } from '../../test/fake-api'
import { dashboard, ownerMe, student, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const invitation = {
  id: 9,
  email: 'nuovo@example.com',
  role: 'teacher',
  students: [],
  status: 'pending',
  expires_at: '2026-11-18T10:00:00Z',
}

const routes = {
  'GET /studio/teachers/': {
    status: 200,
    body: page([{ id: 11, email: 'titolare@example.com', is_owner: true }]),
  },
  'GET /invitations/': { status: 200, body: page([invitation]) },
}

test('the owner invites a teacher and revokes a pending invitation', async () => {
  const api = signedInAs(ownerMe, {
    ...routes,
    'POST /invitations/': { status: 201, body: invitation },
    'POST /invitations/9/revoke/': { status: 200, body: { ...invitation, status: 'revoked' } },
  })
  renderApp('/team')

  expect(await screen.findByText('nuovo@example.com')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'altro@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send invitation' }))
  await waitFor(() => expect(api.callsTo('POST /invitations/')).toHaveLength(1))
  expect(api.callsTo('POST /invitations/')[0].body).toEqual({ email: 'altro@example.com', role: 'teacher' })

  fireEvent.click(screen.getByRole('button', { name: 'Revoke' }))
  await waitFor(() => expect(api.callsTo('POST /invitations/9/revoke/')).toHaveLength(1))
})

test('a teacher cannot open the team page and has no link to it', async () => {
  signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
  renderApp('/team')

  expect(await screen.findByText('Hi, mario.rossi')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Team' })).not.toBeInTheDocument()
})

test('a teacher invites the parent of a student from the student page', async () => {
  const s = student(7)
  const api = signedInAs(teacherMe, {
    'GET /students/7/': { status: 200, body: s },
    'GET /students/7/lessons/': { status: 200, body: [] },
    'POST /invitations/': { status: 201, body: { ...invitation, role: 'parent', students: [7] } },
  })
  renderApp('/students/7')

  fireEvent.click(await screen.findByRole('button', { name: 'Invite parent' }))
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'mamma@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send invitation' }))

  expect(await screen.findByText(/Invitation sent to mamma@example.com/)).toBeInTheDocument()
  expect(api.callsTo('POST /invitations/')[0].body).toEqual({
    email: 'mamma@example.com',
    role: 'parent',
    student_ids: [7],
  })
  expect(screen.queryByRole('button', { name: 'Invite student' })).not.toBeInTheDocument() // a minor
})

test('an adult student without an account gets an "Invite student" button', async () => {
  signedInAs(teacherMe, {
    'GET /students/7/': { status: 200, body: student(7, { is_adult: true, has_account: false }) },
    'GET /students/7/lessons/': { status: 200, body: [] },
  })
  renderApp('/students/7')

  expect(await screen.findByRole('button', { name: 'Invite student' })).toBeInTheDocument()
})
