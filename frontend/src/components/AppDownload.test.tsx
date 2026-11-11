import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import '../i18n'
import { AppDownload } from './AppDownload'

afterEach(() => vi.unstubAllEnvs())

test('with a build link configured, the Android download is offered', () => {
  vi.stubEnv('VITE_ANDROID_APK_URL', 'https://expo.dev/accounts/x/builds/abc')
  render(<AppDownload />)

  const link = screen.getByRole('link', { name: 'Download for Android' })
  expect(link).toHaveAttribute('href', 'https://expo.dev/accounts/x/builds/abc')
  expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText('The iPhone version is not available yet.')).toBeInTheDocument()
})

test('without a link, the landing says it is coming and the signed-in pages show nothing', () => {
  vi.stubEnv('VITE_ANDROID_APK_URL', '')
  const { container, rerender } = render(<AppDownload />)
  expect(container).toBeEmptyDOMElement()

  rerender(<AppDownload showWhenEmpty />)
  expect(screen.getByText('The Android version is coming soon.')).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: /Download/ })).toBeNull()
})

test('an address that is not https is never used as a link', () => {
  vi.stubEnv('VITE_ANDROID_APK_URL', 'javascript:alert(1)')
  render(<AppDownload showWhenEmpty />)

  expect(screen.queryByRole('link', { name: /Download/ })).toBeNull()
  expect(screen.getByText('The Android version is coming soon.')).toBeInTheDocument()
})
