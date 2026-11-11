import type { Dashboard, Lesson, Me, Payment, Student } from '../api/types'

export const teacherMe: Me = {
  id: 1,
  email: 'mario.rossi@example.com',
  role: 'teacher',
  preferred_language: 'en',
  teacher: { id: 10, studio: 100, is_owner: false },
  parent_account: null,
  email_verified: true,
  mfa_enabled: false,
}

export const parentMe: Me = {
  id: 2,
  email: 'anna@example.com',
  role: 'parent',
  preferred_language: 'en',
  teacher: null,
  parent_account: { id: 20 },
  email_verified: true,
  mfa_enabled: false,
}

export const lesson = (over: Partial<Lesson> = {}): Lesson => ({
  id: 1,
  student: 7,
  student_name: 'Giulia Rossi',
  teacher: 10,
  package: 3,
  start_time: '2026-11-10T15:00:00+01:00',
  duration_minutes: 45,
  end_time: '2026-11-10T15:45:00+01:00',
  status: 'scheduled',
  notes: '',
  ...over,
})

export const dashboard = (over: Partial<Dashboard> = {}): Dashboard => ({
  week: [lesson()],
  upcoming: [lesson()],
  pending_payments_count: 2,
  active_students_count: 12,
  low_package_students: [{ id: 7, full_name: 'Giulia Rossi' }],
  ...over,
})

export const student = (id: number, over: Partial<Student> = {}): Student => ({
  id,
  first_name: `Student${id}`,
  last_name: 'Test',
  full_name: `Student${id} Test`,
  instrument: 'Piano',
  teacher: 10,
  studio: 100,
  is_active: true,
  is_adult: false,
  has_account: false,
  active_package: {
    id: 100 + id,
    student: id,
    total_lessons: 10,
    lessons_remaining: 2,
    purchase_date: '2026-10-01',
    expiry_date: null,
    price: '150.00',
    status: 'active',
    is_low: true,
  },
  payment_status: 'pending',
  ...over,
})

export const payment = (id: number, over: Partial<Payment> = {}): Payment => ({
  id,
  student: 7,
  student_name: 'Giulia Rossi',
  package: null,
  amount: '120.00',
  date: '2026-11-02',
  method: 'bank_transfer',
  status: 'paid',
  checkout: null,
  ...over,
})

export const ownerMe: Me = {
  ...teacherMe,
  id: 3,
  email: 'titolare@example.com',
  role: 'studio_owner',
  teacher: { id: 11, studio: 100, is_owner: true },
}

export const studentMe: Me = {
  id: 4,
  email: 'luca@example.com',
  role: 'student',
  preferred_language: 'en',
  teacher: null,
  parent_account: null,
  email_verified: true,
  mfa_enabled: false,
}
