import { Route, Routes } from 'react-router-dom'

import { Login } from './auth/Login'
import { RequireRole } from './auth/RequireRole'
import { Dashboard } from './features/teacher/Dashboard'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireRole roles={['teacher', 'studio_owner']}>
            <Dashboard />
          </RequireRole>
        }
      />
    </Routes>
  )
}

export default App
