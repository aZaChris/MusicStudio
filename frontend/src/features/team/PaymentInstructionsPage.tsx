import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import type { PaymentInstructions } from '../../api/types'
import { useAuth } from '../../auth/useAuth'
import { AppShell } from '../../components/AppShell'
import { ErrorText, QueryState } from '../../components/QueryState'
import { Icon } from '../../components/ui'
import { useInstructions, useSaveInstructions } from '../teacher/api/instructions'
import { PaymentAccountSection } from './PaymentAccountSection'

const MAX_LINKS = 5
type Link = { label: string; url: string }

/**
 * How the studio wants to be paid. The owner edits; teachers read. The IBAN is checked by the
 * server (format and checksum); links must be https. MusicStudio holds and verifies no money.
 */
export function PaymentInstructionsPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const instructions = useInstructions()
  const canEdit = user?.role === 'studio_owner'

  return (
    <AppShell>
      <div className="page-head__text">
        <h1 className="page-title">{t('instructions.title')}</h1>
        <p className="muted">{t('instructions.intro')}</p>
      </div>
      <QueryState query={instructions}>
        {/* Keyed by the save time so the form restarts from what the server stored. */}
        {instructions.data && (
          <InstructionsForm
            key={instructions.data.updated_at ?? 'none'}
            saved={instructions.data}
            canEdit={canEdit}
          />
        )}
      </QueryState>
      {/* Online payments to the studio's own Stripe account: only there once the feature is on. */}
      <PaymentAccountSection canEdit={canEdit} />
    </AppShell>
  )
}

function InstructionsForm({ saved, canEdit }: { saved: PaymentInstructions; canEdit: boolean }) {
  const { t } = useTranslation()
  const save = useSaveInstructions()
  const [holder, setHolder] = useState(saved.account_holder ?? '')
  const [iban, setIban] = useState(saved.iban ?? '')
  const [bank, setBank] = useState(saved.bank_name ?? '')
  const [note, setNote] = useState(saved.note ?? '')
  const [links, setLinks] = useState<Link[]>(saved.links ?? [])

  const setLink = (index: number, patch: Partial<Link>) =>
    setLinks(links.map((link, i) => (i === index ? { ...link, ...patch } : link)))

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate({
      account_holder: holder,
      iban,
      bank_name: bank,
      note,
      // Empty rows are dropped instead of being sent as errors.
      links: links.filter((link) => link.label.trim() || link.url.trim()),
    })
  }

  return (
    <form className="panel ms-form" onSubmit={submit}>
      {!canEdit && (
        <p role="note" className="ms-alert ms-alert--warning" style={{ margin: 0 }}>
          {t('instructions.readOnly')}
        </p>
      )}
      <label className="ms-field">
        {t('instructions.holder')}
        <input
          className="ms-input"
          value={holder}
          maxLength={100}
          readOnly={!canEdit}
          onChange={(e) => setHolder(e.target.value)}
        />
      </label>
      <label className="ms-field">
        {t('instructions.iban')}
        <input
          className="ms-input"
          value={iban}
          maxLength={60}
          autoComplete="off"
          readOnly={!canEdit}
          onChange={(e) => setIban(e.target.value)}
        />
      </label>
      <label className="ms-field">
        {t('instructions.bank')}
        <input
          className="ms-input"
          value={bank}
          maxLength={100}
          readOnly={!canEdit}
          onChange={(e) => setBank(e.target.value)}
        />
      </label>
      <label className="ms-field">
        {t('instructions.note')}
        <input
          className="ms-input"
          value={note}
          maxLength={200}
          readOnly={!canEdit}
          onChange={(e) => setNote(e.target.value)}
        />
        <span className="muted">{t('instructions.noteHint')}</span>
      </label>

      <fieldset className="ms-fieldset">
        <legend>{t('instructions.links')}</legend>
        {links.map((link, index) => (
          <div key={index} className="ms-form__grid">
            <label className="ms-field">
              {t('instructions.linkLabel')}
              <input
                className="ms-input"
                value={link.label}
                maxLength={40}
                readOnly={!canEdit}
                onChange={(e) => setLink(index, { label: e.target.value })}
              />
            </label>
            <label className="ms-field">
              {t('instructions.linkUrl')}
              <input
                className="ms-input"
                type="url"
                inputMode="url"
                placeholder="https://"
                value={link.url}
                maxLength={500}
                readOnly={!canEdit}
                onChange={(e) => setLink(index, { url: e.target.value })}
              />
            </label>
            {canEdit && (
              <button
                type="button"
                className="ms-btn ms-btn--secondary ms-btn--s"
                onClick={() => setLinks(links.filter((_, i) => i !== index))}
              >
                {t('instructions.removeLink')}
              </button>
            )}
          </div>
        ))}
        {canEdit && links.length < MAX_LINKS && (
          <button
            type="button"
            className="ms-btn ms-btn--secondary"
            onClick={() => setLinks([...links, { label: '', url: '' }])}
          >
            {t('instructions.addLink')}
          </button>
        )}
      </fieldset>

      {canEdit && (
        <>
          <button type="submit" className="ms-btn ms-btn--primary ms-btn--l" disabled={save.isPending}>
            {t('instructions.save')}
          </button>
          <ErrorText error={save.error} />
          {save.isSuccess && (
            <p role="status" className="ms-alert ms-alert--success" style={{ margin: 0 }}>
              <Icon name="check" size={18} />
              <span>{t('instructions.saved')}</span>
            </p>
          )}
        </>
      )}
    </form>
  )
}
