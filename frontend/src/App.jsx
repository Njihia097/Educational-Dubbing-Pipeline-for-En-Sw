// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import ProtectedRoute from './components/ProtectedRoute'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Default route → login */}
          <Route path="/" element={<Navigate to="/login" replace />} />

          {/* Public route */}
          <Route path="/login" element={<Login />} />

          {/* Protected dashboard shell with nested routes */}
          <Route
            path="/dashboard/*"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          >
            {/* Index: default dashboard home */}
            <Route index element={<div className="p-6">Welcome to your dashboard.</div>} />

            {/* Upload subpage */}
            <Route path="upload" element={<UploadPage />} />
          </Route>

          {/* Catch-all → login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
