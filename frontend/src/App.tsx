import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Settings, History } from 'lucide-react'
import { AuthProvider } from '@/context/AuthContext'
import { ProtectedRoute, RoleRoute, GuestRoute } from '@/routes/ProtectedRoute'
import { AppShell } from '@/components/layout/AppShell'

import { Landing } from '@/pages/auth/Landing'
import { Login } from '@/pages/auth/Login'
import { Register } from '@/pages/auth/Register'
import { ForgotPassword } from '@/pages/auth/ForgotPassword'
import { ChangePassword } from '@/pages/auth/ChangePassword'

import { StudentDashboard } from '@/pages/student/Dashboard'
import { CreateIssue } from '@/pages/student/CreateIssue'
import { UploadDocuments } from '@/pages/student/UploadDocuments'
import { MyIssues } from '@/pages/student/MyIssues'
import { TrackStatus } from '@/pages/student/TrackStatus'
import { Notifications } from '@/pages/student/Notifications'

import { StaffDashboard } from '@/pages/staff/Dashboard'
import { AssignedIssues } from '@/pages/staff/AssignedIssues'
import { AllIssues } from '@/pages/staff/AllIssues'

import { AdminDashboard } from '@/pages/admin/Dashboard'
import { AdminUsers } from '@/pages/admin/Users'
import { StaffCreate } from '@/pages/admin/StaffCreate'
import { AdminDepartments } from '@/pages/admin/Departments'
import { AdminCategories } from '@/pages/admin/Categories'
import { AdminDocumentTypes } from '@/pages/admin/DocumentTypes'
import { ComingSoon } from '@/pages/admin/ComingSoon'

import { IssueDetailPage } from '@/pages/issues/IssueDetail'
import { Reports } from '@/pages/reports/Reports'
import { Profile } from '@/pages/profile/Profile'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Landing />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />

          {/* Guest-only: an already-authenticated user is bounced to their
              dashboard (or /change-password) instead of seeing these again. */}
          <Route element={<GuestRoute />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>

          {/* Mandatory first-login password change. Authenticated but
              deliberately outside the AppShell/RoleRoute tree -- no
              sidebar/topbar, and ProtectedRoute below redirects here
              whenever must_change_password is true, regardless of role. */}
          <Route path="/change-password" element={<ChangePassword />} />

          {/* Authenticated */}
          <Route element={<ProtectedRoute />}>
            {/* Student */}
            <Route element={<RoleRoute allow={['student']} />}>
              <Route element={<AppShell />}>
                <Route path="/student/dashboard" element={<StudentDashboard />} />
                <Route path="/student/issues/new" element={<CreateIssue />} />
                <Route path="/student/issues/:id/documents" element={<UploadDocuments />} />
                <Route path="/student/issues/:id" element={<IssueDetailPage />} />
                <Route path="/student/issues" element={<MyIssues />} />
                <Route path="/student/track" element={<TrackStatus />} />
                <Route path="/student/notifications" element={<Notifications />} />
                <Route path="/student/profile" element={<Profile />} />
              </Route>
            </Route>

            {/* Staff (course_adviser, hod, ict_officer, exams_officer) */}
            <Route element={<RoleRoute allow={['staff']} />}>
              <Route element={<AppShell />}>
                <Route path="/staff/dashboard" element={<StaffDashboard />} />
                <Route path="/staff/issues/:id" element={<IssueDetailPage />} />
                <Route path="/staff/issues" element={<AllIssues />} />
                <Route path="/staff/all-issues" element={<AllIssues />} />
                <Route path="/staff/reports" element={<Reports />} />
                <Route path="/staff/profile" element={<Profile />} />
              </Route>
            </Route>

            {/* Admin */}
            <Route element={<RoleRoute allow={['admin']} />}>
              <Route element={<AppShell />}>
                <Route path="/admin/dashboard" element={<AdminDashboard />} />
                <Route path="/admin/issues" element={<AllIssues />} />
                <Route path="/admin/issues/:id" element={<IssueDetailPage />} />
                <Route path="/admin/users" element={<AdminUsers />} />
                <Route path="/admin/staff/new" element={<StaffCreate />} />
                <Route path="/admin/departments" element={<AdminDepartments />} />
                <Route path="/admin/categories" element={<AdminCategories />} />
                <Route path="/admin/documents" element={<AdminDocumentTypes />} />
                <Route path="/admin/reports" element={<Reports />} />
                
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
