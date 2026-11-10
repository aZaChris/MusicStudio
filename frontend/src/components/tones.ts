// Which status pill a server value gets. Kept apart from ui.tsx so that file only exports components.
import type { LessonStatus, PaymentStatus } from '../api/types'

export type Tone = 'ok' | 'wait' | 'bad' | 'plan' | 'off' | 'low'

export const paymentTone = (status: PaymentStatus | string | null | undefined): Tone =>
  status === 'paid' ? 'ok' : status === 'overdue' ? 'bad' : 'wait'

export const lessonTone = (status: LessonStatus): Tone =>
  status === 'completed' ? 'ok' : status === 'scheduled' ? 'plan' : 'off'

export const packageTone = (status: string): Tone =>
  status === 'active' ? 'ok' : status === 'expired' ? 'bad' : 'off'
