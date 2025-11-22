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
import SystemOverview from './pages/AdminDashboard/SystemOverview'
import WorkerMonitoring from './pages/AdminDashboard/WorkerMonitoring'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />

          <Route path="/login" element={<Login />} />

          {/* Upload page - standalone full-width page */}
          <Route
            path="/dashboard/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />

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

            {/* Creator: my jobs */}
            <Route path="jobs" element={<MyJobs />} />

            {/* Job detail (shared for creator/admin) */}
            <Route path="job/:jobId" element={<JobDetail />} />

            {/* Admin: all jobs */}
            <Route path="admin/jobs" element={<AdminJobs />} />

            {/* Admin: system overview */}
            <Route path="admin/overview" element={<SystemOverview />} />

            {/* Admin: worker monitoring */}
            <Route path="admin/monitoring" element={<WorkerMonitoring />} />
          </Route>

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
