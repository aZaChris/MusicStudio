import { Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/AuthProvider'
import { Login } from './auth/Login'
import { RequireRole } from './auth/RequireRole'
import { Dashboard } from './features/teacher/Dashboard'
import { Payments } from './features/teacher/Payments'
import { Roster } from './features/teacher/Roster'
import { StudentDetail } from './features/teacher/StudentDetail'
import { ParentPortal } from './features/parent/ParentPortal'

const teacherOnly = ['teacher', 'studio_owner'] as const

function Home() {
  const { user } = useAuth()
  if (user?.role === 'parent') return <ParentPortal />
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
