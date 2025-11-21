// frontend/src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import UploadPage from './pages/UploadPage'
import JobDetail from './pages/JobDetail'
import ProtectedRoute from './components/ProtectedRoute'
import MyJobs from './pages/MyJobs'
import AdminJobs from './pages/AdminJobs'
import DashboardOverview from './pages/DashboardOverview'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />

          <Route path="/login" element={<Login />} />

          {/* Dashboard layout + nested routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          >
            {/* Overview */}
            <Route index element={<DashboardOverview />} />

            {/* Creator upload flow */}
            <Route path="upload" element={<UploadPage />} />

            {/* Creator: my jobs */}
            <Route path="jobs" element={<MyJobs />} />

            {/* Job detail (shared for creator/admin) */}
            <Route path="job/:jobId" element={<JobDetail />} />

            {/* Admin: all jobs */}
            <Route path="admin/jobs" element={<AdminJobs />} />
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
