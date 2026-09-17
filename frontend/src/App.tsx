import { Route, Routes } from 'react-router-dom'

import { Login } from './auth/Login'
import { RequireRole } from './auth/RequireRole'
import { Dashboard } from './features/teacher/Dashboard'
import { Payments } from './features/teacher/Payments'
import { Roster } from './features/teacher/Roster'
import { StudentDetail } from './features/teacher/StudentDetail'

const teacherOnly = ['teacher', 'studio_owner'] as const

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireRole roles={[...teacherOnly]}>
            <Dashboard />
          </RequireRole>
        }
      />
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
