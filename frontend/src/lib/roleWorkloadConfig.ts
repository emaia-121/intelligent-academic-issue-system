import type { Role } from '@/types'

/**
 * Frontend mirror of backend/issues/workflow/definitions.py --
 * WORKFLOW_DEFINITIONS. This file contains NO business logic and makes NO
 * routing/permission decisions -- it is only display configuration for the
 * Staff Dashboard (pages/staff/Dashboard.tsx), which needs to know which
 * categories a given role's work actually touches so it can show a
 * role-appropriate title, queue, and stat cards instead of one generic
 * "staff" view.
 *
 * For each of the 12 WorkflowDefinition entries, a role is considered to
 * "own" that category if it is a participant anywhere in that category's
 * workflow -- i.e. it appears as the starting_role, anywhere in
 * forward_chain, as a key or value in backward_transitions, or in
 * final_authority_roles. This is exactly the same test
 * WorkflowDefinition.involves_role() performs on the backend; the category
 * lists below were derived by applying that test to all 12 definitions by
 * hand, category by category. If issues/workflow/definitions.py changes
 * (a category is added/removed, or a role is added/removed from a
 * category's chain), this file must be updated to match -- there is no
 * backend endpoint that exposes "categories by role" today, so this is a
 * manually-maintained mirror, not a live derivation. Keep it in sync.
 *
 * The actual authorization/routing decision (can this user act on this
 * issue right now) is still made entirely by the backend
 * (issues/workflow/service.py + roles.py) -- this file only decides what
 * the dashboard *displays*, never what a user is *allowed* to do.
 */

/** Every Role except 'student' and 'admin' -- the roles that land on the
 * shared Staff Dashboard (RoleGroup 'staff', see types/index.ts::roleGroup). */
export type StaffRole = Exclude<Role, 'student' | 'admin'>

export interface RoleWorkloadConfig {
  /** Shown in the dashboard's PageHeader instead of the generic
   * "Here's your assigned workload." */
  title: string
  /** Exact Category.name values (categories_category.name / the 12
   * canonical categories the ML classifier and workflow engine both use)
   * this role participates in, in workflow-definition order. */
  categories: string[]
  /** Shown when this role has nothing assigned right now. */
  emptyMessage: string
}

export const ROLE_WORKLOAD_CONFIG: Record<StaffRole, RoleWorkloadConfig> = {
  course_adviser: {
    title: 'Course Adviser Workload',
    categories: ['Missing Result', 'Grade Dispute', 'Course Registration'],
    emptyMessage: 'No Missing Result, Grade Dispute, or Course Registration issues need your attention right now.',
  },
  hod: {
    title: 'HOD Workload',
    // Missing Result (mid-chain), Transcript Request (mid-chain),
    // Academic Clearance (mid-chain + final authority once Department
    // Admin sends back), Examination Issue (mid-chain), and "Other"
    // (starting role -- HOD decides where these get forwarded).
    categories: ['Missing Result', 'Transcript Request', 'Academic Clearance', 'Examination Issue', 'Other'],
    emptyMessage: 'No issues are currently waiting on your review or routing decision.',
  },
  department_admin: {
    title: 'Department Admin Workload',
    categories: ['Missing Result', 'Transcript Request', 'Academic Clearance'],
    emptyMessage: 'No Missing Result, Transcript Request, or Academic Clearance issues need your attention right now.',
  },
  dept_exam_officer: {
    title: 'Department Examination Officer Workload',
    categories: ['Examination Issue'],
    emptyMessage: 'No Examination Issue reports need your attention right now.',
  },
  lecturer: {
    title: 'Lecturer Workload',
    categories: ['Grade Dispute'],
    emptyMessage: 'No Grade Dispute issues need your attention right now.',
  },
  ict_officer: {
    title: 'ICT Officer Workload',
    categories: ['Portal/System Issue'],
    emptyMessage: 'No Portal/System Issue reports need your attention right now.',
  },
  exams_officer: {
    title: 'Exams Officer Workload',
    categories: ['Missing Result', 'Course Registration', 'Transcript Request', 'Examination Issue'],
    emptyMessage: 'No issues from Missing Result, Course Registration, Transcript Request, or Examination Issue need your attention right now.',
  },
  registry: {
    title: 'Registry Workload',
    categories: ['Certificate Collection'],
    emptyMessage: 'No Certificate Collection requests need your attention right now.',
  },
  bursary: {
    title: 'Bursary Workload',
    categories: ['School Fees Issue', 'Certificate Collection'],
    emptyMessage: 'No School Fees Issue or Certificate Collection requests need your attention right now.',
  },
  school_admin_office: {
    title: 'School Administration Workload',
    categories: ['Admission Issue'],
    emptyMessage: 'No Admission Issue reports need your attention right now.',
  },
  student_affairs_officer: {
    title: 'Student Affairs Workload',
    categories: ['Student Welfare'],
    emptyMessage: 'No Student Welfare issues need your attention right now.',
  },
}

/**
 * Mirror of WorkflowDefinition.starting_role for each of the 12 canonical
 * categories (issues/workflow/definitions.py). This is a narrower,
 * separate piece of information from ROLE_WORKLOAD_CONFIG above (which
 * lists every role a category's workflow ever touches) -- this map answers
 * "which single role receives an issue of this category first."
 *
 * Why this matters: issues/workflow/service.py::perform_initial_assignment()
 * is the ONLY place Issue.assigned_to is ever left None -- it looks up
 * exactly this role (definition.starting_role) via find_officer_for_role()
 * and leaves the issue unassigned only if that lookup fails
 * (NoOfficerAvailableError) or the category has no WorkflowDefinition at
 * all. forward_issue()/send_back_issue() never leave an issue unassigned:
 * if they can't find the next/previous officer, the action itself fails
 * with an error instead of silently clearing assigned_to. So for any
 * unassigned issue, this map is sufficient (and correct) to answer "which
 * role should have received this" -- used by the Admin Dashboard's
 * Unassigned by Role widget (pages/admin/Dashboard.tsx).
 */
export const CATEGORY_STARTING_ROLE: Record<string, StaffRole> = {
  'Missing Result': 'course_adviser',
  'Grade Dispute': 'course_adviser',
  'Course Registration': 'course_adviser',
  'Transcript Request': 'department_admin',
  'School Fees Issue': 'bursary',
  'Academic Clearance': 'department_admin',
  'Admission Issue': 'school_admin_office',
  'Certificate Collection': 'registry',
  'Examination Issue': 'dept_exam_officer',
  'Portal/System Issue': 'ict_officer',
  'Student Welfare': 'student_affairs_officer',
  Other: 'hod',
}

/**
 * Fixed display order for staff-role breakdowns on the Admin Dashboard
 * (e.g. the "Staff Coverage by Role" widget) -- intentionally not
 * alphabetical. Groups the 5 department-scoped roles first (Course
 * Adviser through Lecturer), then the 6 central roles (ICT Officer through
 * Student Affairs Officer) -- the same grouping
 * issues/workflow/definitions.py itself draws between
 * DEPARTMENT_SCOPED_ROLES and CENTRAL_ROLES. Excludes 'student' and
 * 'admin', which are not workflow-participating staff roles.
 */
export const STAFF_ROLE_DISPLAY_ORDER: StaffRole[] = [
  'course_adviser',
  'hod',
  'department_admin',
  'dept_exam_officer',
  'lecturer',
  'ict_officer',
  'exams_officer',
  'registry',
  'bursary',
  'school_admin_office',
  'student_affairs_officer',
]

export interface RoleCount {
  role: StaffRole
  count: number
}

/**
 * Converts a staff directory (GET /api/accounts/staff/directory/, already
 * wrapped by api/auth.ts::getStaffDirectory()) into one count per role, in
 * STAFF_ROLE_DISPLAY_ORDER. Every role in that order is always present in
 * the result -- including with a count of 0 -- so a staffing gap (e.g.
 * zero Lecturers) is visible rather than silently missing from the list.
 * Pure counting only: no workflow, routing, or assignment decision is made
 * here, and nothing here calls the API itself -- callers pass in data they
 * already fetched.
 */
export function buildRoleCounts(staff: { role: Role }[]): RoleCount[] {
  return STAFF_ROLE_DISPLAY_ORDER.map((role) => ({
    role,
    count: staff.filter((s) => s.role === role).length,
  }))
}
