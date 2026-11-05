/**
 * Types mirroring the real Django backend (accounts, issues, categories,
 * departments, documents_app apps) plus a small set of admin/reporting
 * types that don't have a backend endpoint yet (marked MOCK-ONLY below).
 */

// ---------------------------------------------------------------------------
// Accounts / roles
// ---------------------------------------------------------------------------

/**
 * Matches accounts.constants.ROLE_CHOICES exactly (backend/accounts/constants.py
 * is the source of truth). The UI groups these into three broad areas (see
 * roleGroup()): 'student' -> student module, 'admin' -> admin module,
 * everything else -> staff module.
 *
 * The six roles below 'admin' were added to the backend to support the
 * 12-category workflow engine (issues/workflow/definitions.py) -- each is a
 * real starting_role/forward_chain/backward_transition/final-authority
 * destination for at least one category. Without them present here,
 * StaffCreate could not create accounts for these roles and the workflow
 * engine's automatic assignment would permanently fall back to
 * "Unassigned" for every category that routes through one of them.
 */
export type Role =
  | 'student'
  | 'course_adviser'
  | 'hod'
  | 'ict_officer'
  | 'exams_officer'
  | 'student_affairs_officer'
  | 'admin'
  | 'department_admin'
  | 'lecturer'
  | 'bursary'
  | 'registry'
  | 'school_admin_office'
  | 'dept_exam_officer'

/** Every Role except 'student' -- mirrors accounts.constants.STAFF_ROLE_CHOICES
 * exactly, which is what the real staff-creation endpoint accepts. */
export const STAFF_ROLES: Role[] = [
  'course_adviser',
  'hod',
  'ict_officer',
  'exams_officer',
  'student_affairs_officer',
  'admin',
  'department_admin',
  'lecturer',
  'bursary',
  'registry',
  'school_admin_office',
  'dept_exam_officer',
]

export type RoleGroup = 'student' | 'staff' | 'admin'

export function roleGroup(role: Role): RoleGroup {
  if (role === 'student') return 'student'
  if (role === 'admin') return 'admin'
  return 'staff'
}

export const ROLE_LABELS: Record<Role, string> = {
  student: 'Student',
  course_adviser: 'Course Adviser',
  hod: 'HOD',
  ict_officer: 'ICT Officer',
  exams_officer: 'Exams Officer',
  student_affairs_officer: 'Student Affairs Officer',
  admin: 'Admin',
  department_admin: 'Department Administrative Office',
  lecturer: 'Lecturer',
  bursary: 'Bursary Office',
  registry: 'Registry',
  school_admin_office: 'School Administration Office',
  dept_exam_officer: 'Department Examination Officer',
}

/**
 * Roles whose department-scoped routing (issues/workflow/roles.py ->
 * find_officer_for_role) filters candidate officers by the issue's
 * student's own UserProfile.department_name -- i.e. these roles only make
 * sense attached to a real academic department. Mirrors
 * DEPARTMENT_SCOPED_ROLES in issues/workflow/definitions.py exactly.
 *
 * Every other staff role (the complement of this set within STAFF_ROLES,
 * excluding 'admin') is resolved institution-wide with no department
 * scoping at all (CENTRAL_ROLES on the backend) -- an academic department
 * is meaningless for those accounts.
 */
export const DEPARTMENT_SCOPED_ROLES: Role[] = [
  'course_adviser',
  'hod',
  'lecturer',
  'department_admin',
  'dept_exam_officer',
]

export function isDepartmentScopedRole(role: Role | ''): boolean {
  return role !== '' && DEPARTMENT_SCOPED_ROLES.includes(role)
}

/**
 * The 31 real academic departments at FUPRE. This is the canonical list
 * used anywhere a person (student, or staff in a department-scoped role)
 * needs to be attached to a real academic department -- replacing the
 * temporary 5-entry mock catalogue (src/api/mock/store.ts's
 * SEED_DEPARTMENTS/listDepartments) that Register.tsx and StaffCreate.tsx
 * used to source from, which contained administrative offices
 * (Bursary, ICT, Transport, etc.) rather than academic departments and
 * caused department-scoped workflow routing to fail for real accounts.
 *
 * NOTE: this is deliberately just a flat name list, not a `Department`
 * model/table -- the larger Department redesign (FK, `kind`, real CRUD/API)
 * is out of scope here and remains a separate, postponed task. This list
 * only fixes what UserProfile.department_name gets populated with.
 */
export const ACADEMIC_DEPARTMENTS: string[] = [
  'Biochemistry',
  'Chemistry',
  'Environmental Management & Toxicology',
  'Geology',
  'Applied Geophysics',
  'Industrial Chemistry',
  'Mathematics',
  'Petroleum Chemistry',
  'Physics',
  'Science Laboratory Technology',
  'Statistics',
  'Chemical Engineering',
  'Civil Engineering',
  'Computer Engineering',
  'Electrical/Electronic Engineering',
  'Marine Engineering',
  'Mechanical Engineering',
  'Natural Gas Engineering',
  'Petrochemical Engineering',
  'Petroleum Engineering',
  'Computer Science',
  'Cyber Security',
  'Data Science',
  'Information Technology',
  'Software Engineering',
  'Maritime Economics & Finance',
  'Maritime Transport & Logistics',
  'Entrepreneurship',
  'Logistics & Supply Chain Management',
  'Petroleum Information Management',
  'Procurement Management',
]

/**
 * The real login response (POST /api/accounts/login/, see
 * accounts/auth_serializers.py) returns exactly:
 *   { id, first_name, last_name, email, role, must_change_password }
 * -- no username. Django's User.username is set equal to email under the
 * hood for every account created via registration/staff-creation, but the
 * API never exposes it, so the frontend no longer treats "username" as part
 * of a real session.
 *
 * `username`, `matric_number`, `staff_id`, `level`, `phone_number` and
 * `is_active` stay on this type only because the MOCK admin "Users"
 * management records (src/api/mock/store.ts) still use them -- there's no
 * `/api/accounts/me/` endpoint yet, so a real logged-in user's profile never
 * populates those fields.
 */
export interface UserProfile {
  id: number
  email: string
  first_name: string
  last_name: string
  role: Role
  must_change_password?: boolean
  username?: string
  matric_number?: string | null
  staff_id?: string | null
  phone_number?: string | null
  department_name?: string | null
  level?: string | null
  is_active?: boolean
}

// ---------------------------------------------------------------------------
// Issues (backed by the real API: /api/issues/...)
// ---------------------------------------------------------------------------

export type IssueStatus =
  | 'pending'
  | 'ready_for_review'
  | 'in_progress'
  | 'resolved'
  | 'closed'

export const ISSUE_STATUS_LABELS: Record<IssueStatus, string> = {
  pending: 'Pending',
  ready_for_review: 'Under Review',
  in_progress: 'In Progress',
  resolved: 'Resolved',
  closed: 'Closed',
}

export interface IssueDocumentRecord {
  id: number
  document: string // document name (serializer exposes name, not id)
  file: string // URL/path returned by Django's FileField
  uploaded_at: string
}

export interface IssueActivityRecord {
  id: number
  action: string
  performed_by: string | null // username, or "System", or null
  is_system_action: boolean
  notes: string | null
  created_at: string
}

/** Shape returned by IssueSerializer (list + detail base fields). */
export interface Issue {
  id: number
  title: string
  description: string
  student: string // username
  assigned_to: string | null // email
  category: string // name
  department: string // name
  status: IssueStatus
  is_complete: boolean
  resolution_notes: string | null
  information_request: string | null
  student_information_response: string | null 
  created_at: string
  resolved_at: string | null 
}

/** Shape returned by IssueDetailSerializer (adds documents + activity +
 * updated_at + required_documents). */
export interface IssueDetail extends Issue {
  documents: IssueDocumentRecord[]
  activity_history: IssueActivityRecord[]
  updated_at: string
  /** The category's full required-document list (id/name only), sourced
   * from Category.required_documents() -- independent of which of them
   * have actually been uploaded (see `documents` above). */
  required_documents: RequiredDocumentChecklistItem[]
}

export interface RequiredDocumentChecklistItem {
  document_id: number
  document_name: string
}

/** Shape returned by POST /api/issues/create/ (data field) once the issue
 * has actually been created -- either immediately (high-confidence ML
 * prediction) or on the second call of the confirm/manual-selection
 * exception path. */
export interface CreateIssueResult {
  status: 'created'
  issue_id: number
  title: string
  category: string
  assigned_to: string | null
  required_documents: RequiredDocumentChecklistItem[]
}

/** The category the ML classifier predicted -- id + name only. Confidence
 * is deliberately not part of this type: it is a backend concern the
 * frontend never displays (see CreateIssueAPIView on the backend). */
export interface PredictedCategory {
  id: number
  name: string
}

/** Shape returned by POST /api/issues/create/ (data field) when the
 * classifier could not create the issue outright -- either it wants the
 * student to confirm its guess ('confirmation_required', medium
 * confidence) or wants the student to pick a category manually
 * ('manual_selection_required', low confidence). No issue exists yet. */
export interface CreateIssuePendingResult {
  status: 'confirmation_required' | 'manual_selection_required'
  predicted_category: PredictedCategory
  requires_confirmation: boolean
  requires_manual_review: boolean
}

export type CreateIssueResponse = CreateIssueResult | CreateIssuePendingResult

/** Shape returned by GET /api/categories/ -- the real, canonical Category
 * table (12 rows). Used only for the manual-selection exception path
 * (confirmation rejected, or low-confidence review); the normal
 * high-confidence flow never needs the student to see this list. */
export interface CategoryOption {
  id: number
  name: string
  department: string
}

/** Shape returned by POST /api/issues/:id/upload-document/ (data field). */
export interface UploadDocumentResult {
  issue_id: number
  document_uploaded: string
  is_complete: boolean
  status: IssueStatus
  missing_documents: string[]
}

/** Generic envelope every real endpoint responds with. */
export interface ApiEnvelope<T> {
  success: boolean
  message: string
  data?: T
  errors?: Record<string, string[]> | null
}

// ---------------------------------------------------------------------------
// Categories / Departments / Document types
// MOCK-ONLY below this line: categories, departments and documents_app exist
// as Django apps with models, but views.py in each is still the empty
// scaffold Django generates -- there is no API surface for them yet. These
// types back the mock data layer in src/api/mock/ until real endpoints ship.
// ---------------------------------------------------------------------------

export interface Department {
  id: number
  name: string
  kind: 'academic' | 'administrative'
  description?: string | null
} 

export interface DocumentType {
  id: number
  name: string
  description?: string | null
}

export interface Category {
  id: number
  name: string
  description?: string | null
  department: string // department name
  department_id: number
  documents: DocumentType[] // required documents for this category
}

// ---------------------------------------------------------------------------
// Admin reporting -- MOCK-ONLY, no analytics endpoint exists yet.
// ---------------------------------------------------------------------------

export interface AdminOverviewStats {
  total_users: number
  total_departments: number
  total_categories: number
  open_issues: number
  issues_by_status: Record<IssueStatus, number>
  total_issues: number
}

export interface IssueTrendPoint {
  label: string
  submitted: number
  resolved: number
}

export interface DepartmentSummary {
  department: string
  open: number
  resolved: number
  avg_resolution_days: number
}
