// The page a visitor sees before signing in (the "shop window" with a way to start).
import { fireEvent, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

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

  expect((await screen.findAllByRole('link', { name: 'Inizia gratis' }))[0]).toHaveAttribute(
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

test('the landing shows real phone screens that follow the theme', async () => {
  installFakeApi()
  renderApp('/')

  expect(await screen.findByRole('heading', { name: 'Take a look inside' })).toBeInTheDocument()
  const parent = screen.getByRole('img', { name: 'The parent portal' })
  const before = parent.getAttribute('src')
  fireEvent.click(screen.getByRole('button', { name: /dark|light/i }))
  expect(parent.getAttribute('src')).not.toBe(before)
  expect(parent.getAttribute('src')).toMatch(/^\/showcase\/parent-(light|dark)\.jpg$/)
})

test('the brand video waits for a click, then plays with its controls', async () => {
  installFakeApi()
  const play = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  const { container } = renderApp('/')

  expect(await screen.findByRole('heading', { name: 'See it in motion' })).toBeInTheDocument()
  const video = container.querySelector('video')!
  expect(video).toHaveAttribute('aria-label', 'Video: a tour of MusicStudio')
  expect(video).toHaveAttribute('preload', 'none') // nothing downloaded before the click
  expect(video).not.toHaveAttribute('autoplay')
  expect(play).not.toHaveBeenCalled()

  fireEvent.click(screen.getByRole('button', { name: 'Play · 0:28' }))

  expect(play).toHaveBeenCalledOnce()
  expect(video).toHaveAttribute('controls')
  expect(screen.queryByRole('button', { name: 'Play · 0:28' })).not.toBeInTheDocument()
  play.mockRestore()
})

test('the main call to action starts a free account, with sign-in one click away', async () => {
  installFakeApi()
  renderApp('/')

  const starts = await screen.findAllByRole('link', { name: 'Start for free' })
  expect(starts.length).toBeGreaterThanOrEqual(3) // top bar, hero, closing section
  for (const link of starts) expect(link).toHaveAttribute('href', '/register')
  expect(screen.getByText('Already have an account?')).toBeInTheDocument()
})
