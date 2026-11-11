import { Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/useAuth'
import { AcceptInvitation } from './auth/AcceptInvitation'
import { ConfirmEmail } from './auth/ConfirmEmail'
import { ForgotPassword } from './auth/ForgotPassword'
import { Login } from './auth/Login'
import { Register } from './auth/Register'
import { ResetPassword } from './auth/ResetPassword'
import { RequireRole } from './auth/RequireRole'
import { Dashboard } from './features/teacher/Dashboard'
import { Payments } from './features/teacher/Payments'
import { Roster } from './features/teacher/Roster'
import { StudentDetail } from './features/teacher/StudentDetail'
import { ParentPortal } from './features/parent/ParentPortal'
import { AccountPage } from './features/account/AccountPage'
import { AuditPage } from './features/audit/AuditPage'
import { PrivacyPage } from './features/privacy/PrivacyPage'
import { TeamPage } from './features/team/TeamPage'

const teacherOnly = ['teacher', 'studio_owner'] as const
const familyRoles = ['parent', 'student'] as const

function Home() {
  const { user } = useAuth()
  if (user?.role === 'parent' || user?.role === 'student') return <ParentPortal />
  return (
    <RequireRole roles={[...teacherOnly]}>
      <Dashboard />
    </RequireRole>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/confirm-email" element={<ConfirmEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/invitations/accept" element={<AcceptInvitation />} />
      <Route path="/" element={<Home />} />
      <Route
        path="/students"
        element={
          <RequireRole roles={[...teacherOnly]}>
            <Roster />
          </RequireRole>
        }
      />
      <Route
        path="/students/:id"
        element={
          <RequireRole roles={[...teacherOnly]}>
            <StudentDetail />
          </RequireRole>
        }
      />
      <Route
        path="/account"
        element={
          <RequireRole roles={[...teacherOnly]}>
            <AccountPage />
          </RequireRole>
        }
      />
      <Route
        path="/team"
        element={
          <RequireRole roles={['studio_owner']}>
            <TeamPage />
          </RequireRole>
        }
      />
      <Route
        path="/audit"
        element={
          <RequireRole roles={['studio_owner']}>
            <AuditPage />
          </RequireRole>
        }
      />
      <Route
        path="/privacy"
        element={
          <RequireRole roles={[...familyRoles]}>
            <PrivacyPage />
          </RequireRole>
        }
      />
      <Route
        path="/payments"
        element={
          <RequireRole roles={[...teacherOnly]}>
            <Payments />
          </RequireRole>
        }
      />
    </Routes>
  )
}

export default App
