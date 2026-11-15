// The studio's payment instructions: the owner edits, teachers only read (US3).
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, test } from 'vitest'

import { ownerMe, teacherMe } from '../../test/fixtures'
import { renderApp, signedInAs } from '../../test/utils'

const saved = {
  account_holder: 'Studio Armonia SRL',
  iban: 'IT60X0542811101000000123456',
  bank_name: 'Banca Esempio',
  note: 'Write the student name',
  links: [{ label: 'PayPal', url: 'https://paypal.me/armonia' }],
  updated_at: '2026-11-15T10:00:00Z',
}
const empty = { ...saved, account_holder: '', iban: '', bank_name: '', note: '', links: [], updated_at: null }

test('the owner sees the saved details and saves a change', async () => {
  const api = signedInAs(ownerMe, {
    'GET /payment-instructions/': { status: 200, body: saved },
    'PUT /payment-instructions/': { status: 200, body: { ...saved, note: 'New note' } },
  })
  renderApp('/payment-instructions')

  expect(await screen.findByLabelText('IBAN')).toHaveValue(saved.iban)
  expect(screen.getByLabelText('Account holder')).toHaveValue('Studio Armonia SRL')
  fireEvent.change(screen.getByLabelText(/Note for parents/), { target: { value: 'New note' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(api.callsTo('PUT /payment-instructions/')).toHaveLength(1))
  expect(api.callsTo('PUT /payment-instructions/')[0].body).toEqual({
    account_holder: 'Studio Armonia SRL',
    iban: saved.iban,
    bank_name: 'Banca Esempio',
    note: 'New note',
    links: [{ label: 'PayPal', url: 'https://paypal.me/armonia' }],
  })
  expect(await screen.findByText('Saved.')).toBeInTheDocument()
})

test("the server's field error is shown and what was typed is kept", async () => {
  signedInAs(ownerMe, {
    'GET /payment-instructions/': { status: 200, body: empty },
    'PUT /payment-instructions/': {
      status: 400,
      body: { iban: ['This IBAN is not valid. Check it and try again.'] },
    },
  })
  renderApp('/payment-instructions')

  fireEvent.change(await screen.findByLabelText('IBAN'), { target: { value: 'IT00WRONG' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  expect(await screen.findByText(/iban: This IBAN is not valid/)).toBeInTheDocument()
  expect(screen.getByLabelText('IBAN')).toHaveValue('IT00WRONG')
})

test('links can be added up to five and removed; empty rows are not sent', async () => {
  const api = signedInAs(ownerMe, {
    'GET /payment-instructions/': { status: 200, body: empty },
    'PUT /payment-instructions/': { status: 200, body: empty },
  })
  renderApp('/payment-instructions')

  for (let i = 0; i < 5; i += 1) {
    fireEvent.click(await screen.findByRole('button', { name: 'Add a link' }))
  }
  expect(screen.queryByRole('button', { name: 'Add a link' })).not.toBeInTheDocument() // the sixth
  fireEvent.click(screen.getAllByRole('button', { name: 'Remove' })[4])
  expect(screen.getAllByLabelText('Label')).toHaveLength(4)
  fireEvent.change(screen.getAllByLabelText('Label')[0], { target: { value: 'Satispay' } })
  fireEvent.change(screen.getAllByLabelText('Address')[0], { target: { value: 'https://s.example/x' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(api.callsTo('PUT /payment-instructions/')).toHaveLength(1))
  expect((api.callsTo('PUT /payment-instructions/')[0].body as { links: unknown[] }).links).toEqual([
    { label: 'Satispay', url: 'https://s.example/x' },
  ])
})

test('a teacher can read the details but has nothing to change them with', async () => {
  signedInAs(teacherMe, { 'GET /payment-instructions/': { status: 200, body: saved } })
  renderApp('/payment-instructions')

  expect(await screen.findByLabelText('IBAN')).toHaveValue(saved.iban)
  expect(screen.getByLabelText('IBAN')).toHaveAttribute('readonly')
  expect(screen.getByText('Only the studio owner can change these details.')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Add a link' })).not.toBeInTheDocument()
})
