// Short names for the generated contract types (ADR-024). Never hand-write a response shape.
import type { components } from './schema'

type Schemas = components['schemas']

export type Me = Schemas['Me']
export type Role = Schemas['RoleEnum']
export type Dashboard = Schemas['Dashboard']
export type Lesson = Schemas['Lesson']
export type LessonStatus = Schemas['LessonStatusEnum']
export type Student = Schemas['Student']
export type Payment = Schemas['Payment']
export type PaymentRequest = Schemas['PaymentRequest']
export type PaymentMethod = Schemas['MethodEnum']
export type PaymentStatus = Schemas['PaymentStatusEnum']
export type TokenPair = Schemas['TokenObtainPair']
