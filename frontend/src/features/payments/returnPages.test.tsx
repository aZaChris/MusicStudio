// Where Stripe sends the payer back to (US2, phase 9): the page never claims the payment succeeded.
import { screen } from '@testing-library/react'
import { expect, test } from 'vitest'

import { parentMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

test('the success page says the payment is being confirmed and asks not to pay twice', async () => {
  signedInAs(parentMe)
  renderApp('/payments/success')

  expect(await screen.findByText(/confirming your payment/)).toBeInTheDocument()
  expect(screen.getByText(/do not pay again/i)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Back to your lessons' })).toHaveAttribute('href', '/')
})

test('the cancel page says nothing was charged', async () => {
  signedInAs(parentMe)
  renderApp('/payments/cancel')

  expect(await screen.findByText('Payment cancelled')).toBeInTheDocument()
  expect(screen.getByText(/Nothing was charged/)).toBeInTheDocument()
})
