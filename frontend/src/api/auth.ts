import { apiClient, tokenStorage } from './client'
import type { ApiEnvelope, Role, UserProfile } from '@/types'

/**
 * Verified directly against the Django project (accounts app):
 *   POST /api/accounts/login/    -- EmailLoginView, email + password, returns
 *                                    { access, refresh, user: { id, first_name,
 *                                    last_name, email, role, must_change_password } }
 *   POST /api/accounts/register/ -- StudentRegistrationView (AllowAny)
 *   POST /api/accounts/staff/    -- StaffAccountCreationView (admin only)
 *
 * The old default-SimpleJWT `/api/token/` endpoint still exists on the
 * backend but the app no longer uses it -- accounts/services.py sets
 * `User.username = email` for every account it creates, and login is
 * email-based end to end now. There is still no `/api/accounts/me/`
 * endpoint, so anything beyond what the login response returns (matric
 * number, staff ID, level, phone number) is not available for a real
 * session.
 */

const PROFILE_KEY = 'sims.profile'

export interface LoginPayload {
  email: string
  password: string
}

interface LoginResponseUser {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role
  must_change_password: boolean
}

interface LoginResponseData {
  access: string
  refresh: string
  user: LoginResponseUser
}

export interface LoginResult {
  access: string
  refresh: string
  profile: UserProfile
}

export async function login({ email, password }: LoginPayload): Promise<LoginResult> {
  const res = await apiClient.post<ApiEnvelope<LoginResponseData>>('/accounts/login/', { email, password })
  if (!res.data.data) throw new Error(res.data.message || 'Login failed.')

  const { access, refresh, user } = res.data.data
  tokenStorage.set(access, refresh)

  const profile: UserProfile = {
    id: user.id,
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    role: user.role,
    must_change_password: user.must_change_password,
  }
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile))

  return { access, refresh, profile }
}

export function getStoredProfile(): UserProfile | null {
  const raw = localStorage.getItem(PROFILE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserProfile
  } catch {
    return null
  }
}

/** Merges a patch into the stored profile (e.g. clearing must_change_password
 * after a successful password change) without a round-trip -- there's no
 * `/me/` endpoint to re-fetch from. */
export function patchStoredProfile(patch: Partial<UserProfile>): UserProfile | null {
  const current = getStoredProfile()
  if (!current) return null
  const updated: UserProfile = { ...current, ...patch }
  localStorage.setItem(PROFILE_KEY, JSON.stringify(updated))
  return updated
}

export function logout() {
  tokenStorage.clear()
  localStorage.removeItem(PROFILE_KEY)
}

// ---------------------------------------------------------------------------
// Student registration -- REAL, POST /api/accounts/register/. Matches
// accounts.serializers.StudentRegistrationSerializer field-for-field.
// ---------------------------------------------------------------------------

export interface RegisterPayload {
  first_name: string
  last_name: string
  email: string
  matric_number: string
  phone_number: string
  department_name: string
  level: string
  password: string
  confirm_password: string
}

export interface RegisterResult {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role
}

export async function registerStudent(payload: RegisterPayload): Promise<RegisterResult> {
  const res = await apiClient.post<ApiEnvelope<RegisterResult>>('/accounts/register/', payload)
  if (!res.data.data) throw new Error(res.data.message || 'Registration failed.')
  return res.data.data
}

// ---------------------------------------------------------------------------
// Staff account creation -- REAL, POST /api/accounts/staff/. Admin-only on
// the backend (IsSystemAdmin); matches
// accounts.serializers.StaffAccountCreationSerializer field-for-field. The
// backend generates and returns a temporary password -- there's nothing to
// invent here.
// ---------------------------------------------------------------------------

export interface CreateStaffPayload {
  first_name: string
  last_name: string
  email: string
  phone_number: string
  department_name: string
  staff_id: string
  role: Role
}

export interface CreateStaffResult {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role
  temporary_password: string
}

export async function createStaffAccount(payload: CreateStaffPayload): Promise<CreateStaffResult> {
  const res = await apiClient.post<ApiEnvelope<CreateStaffResult>>('/accounts/staff/', payload)
  if (!res.data.data) throw new Error(res.data.message || 'Could not create staff account.')
  return res.data.data
}

// ---------------------------------------------------------------------------
// Change password -- the mandatory first-login flow the product spec
// requires. IMPORTANT: verified directly against the Django project --
// accounts/urls.py only registers register/, login/, and staff/. There is no
// change-password view, serializer, or route anywhere in the backend yet, so
// this call will 404 until one exists. Wire it up as:
//   POST /api/accounts/change-password/  (IsAuthenticated)
//   body: { current_password, new_password, confirm_new_password }
//   on success: verify current_password, User.set_password(new_password),
//               UserProfile.must_change_password = False, save both.
// The frontend flow (src/pages/auth/ChangePassword.tsx) is fully built
// against this contract so it starts working the moment the endpoint ships.
// ---------------------------------------------------------------------------

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
  confirm_new_password: string
}

export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await apiClient.post('/accounts/change-password/', payload)
}

// ---------------------------------------------------------------------------
// Staff directory -- REAL, GET /api/accounts/staff/directory/. Admin-only
// (IsSystemAdmin), matches accounts.views.StaffDirectoryAPIView. Added to
// support the Administrative Assignment Management officer picker on the
// issue detail page -- there was previously no way to list existing staff
// accounts from the frontend at all (admin/Users.tsx still runs entirely
// against mock data; this is the first real staff-listing call in the app).
// ---------------------------------------------------------------------------

export interface StaffDirectoryEntry {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role
  department_name: string | null
}

export async function getStaffDirectory(): Promise<StaffDirectoryEntry[]> {
  const res = await apiClient.get<ApiEnvelope<StaffDirectoryEntry[]>>('/accounts/staff/directory/')
  return res.data.data ?? []
}

export interface CurrentUserProfileResult {
  id: number
  first_name: string
  last_name: string
  email: string
  role: Role
  department_name: string | null
  staff_id: string | null
  matric_number: string | null
  level: string | null
  phone_number: string | null
  must_change_password: boolean
} 

export async function getCurrentUserProfile(): Promise<CurrentUserProfileResult> {
  const res = await apiClient.get<ApiEnvelope<CurrentUserProfileResult>>('/accounts/me/')

  if (!res.data.data) {
    throw new Error(res.data.message || 'Could not load profile.')
  }

  return res.data.data
} 