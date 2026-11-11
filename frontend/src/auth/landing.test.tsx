// The page a visitor sees before signing in (the "shop window" with a way to start).
import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'

import i18n from '../i18n'

import { installFakeApi } from '../test/fake-api'
import { dashboard, teacherMe } from '../test/fixtures'
import { renderApp, signedInAs } from '../test/utils'

afterEach(() => i18n.changeLanguage('en')) // a test must not leave the language switched

test('the landing explains the product with real features and honest safety points', async () => {
  installFakeApi()
  renderApp('/')

  expect(await screen.findByRole('heading', { name: 'What it does' })).toBeInTheDocument()
  for (const name of ['Lessons', 'Packages', 'Payments', 'Parents']) {
    expect(screen.getByRole('heading', { name })).toBeInTheDocument()
  }
  expect(screen.getByText("Teachers' notes are encrypted.")).toBeInTheDocument()
  expect(screen.getByText(/You join by invitation/i)).toBeInTheDocument()
})

test('the landing speaks Italian on request', async () => {
  installFakeApi()
  renderApp('/')

  fireEvent.click(await screen.findByRole('button', { name: 'Passa all’italiano' }))

  expect((await screen.findAllByRole('link', { name: "Crea l'account del tuo studio" }))[0]).toHaveAttribute(
    'href',
    '/register',
  )
  expect(screen.getByRole('heading', { name: 'Cosa fa' })).toBeInTheDocument()
})

test('a signed-in teacher does not see the landing', async () => {
  signedInAs(teacherMe, { 'GET /dashboard/': { status: 200, body: dashboard() } })
  renderApp('/')

  expect(await screen.findByText('Hi, mario.rossi')).toBeInTheDocument()
  expect(screen.queryByText('What it does')).not.toBeInTheDocument()
})
