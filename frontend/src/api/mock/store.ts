/**
 * MOCK DATA LAYER.
 *
 * Backs the Admin module's User / Department / Category / Document Type
 * management screens. Verified against the real Django project: the
 * `departments`, `categories`, `documents_app` and `accounts` apps all have
 * models but their `views.py` files are still the empty scaffold Django
 * generates -- none of them are wired into `student_issue_system/urls.py`.
 * So there is no real API to call for CRUD on these entities yet.
 *
 * This module persists to localStorage so edits survive a refresh within a
 * demo session, and every function is `async` with a small artificial delay
 * so swapping in real `apiClient` calls later doesn't change any call sites.
 */
import type { Category, Department, DocumentType, Role, UserProfile } from '@/types'
import { STAFF_ROLES } from '@/types'

const DELAY = 350
const wait = () => new Promise((r) => setTimeout(r, DELAY))

function load<T>(key: string, seed: T): T {
  const raw = localStorage.getItem(key)
  if (!raw) {
    localStorage.setItem(key, JSON.stringify(seed))
    return seed
  }
  try {
    return JSON.parse(raw) as T
  } catch {
    return seed
  }
}

function save<T>(key: string, value: T) {
  localStorage.setItem(key, JSON.stringify(value))
}

// ---------------------------------------------------------------------------
// Seed data
// ---------------------------------------------------------------------------

const SEED_DOCUMENT_TYPES: DocumentType[] = [
  { id: 1, name: 'Student ID', description: 'Copy of the student identity card.' },
  { id: 2, name: 'Photo of the Issue', description: 'Clear photo showing the reported issue.' },
  { id: 3, name: 'Hostel Allotment Proof', description: 'Proof of hostel room allocation.' },
  { id: 4, name: 'Fee Payment Receipt', description: 'Receipt confirming payment.' },
  { id: 5, name: 'Medical Report', description: 'Supporting medical documentation, if applicable.' },
  { id: 6, name: 'Course Registration Form', description: 'Current semester course registration.' },
]

const SEED_DEPARTMENTS: Department[] = [
  { id: 1, name: 'Hostel Administration', description: 'Handles accommodation-related issues.', assigned_officer: 'officer01' },
  { id: 2, name: 'ICT', description: 'Handles technical and systems issues.', assigned_officer: 'ict_officer01' },
  { id: 3, name: 'Bursary', description: 'Handles fee and payment issues.', assigned_officer: 'bursary01' },
  { id: 4, name: 'Exams & Records', description: 'Handles exam and result issues.', assigned_officer: 'exams01' },
  { id: 5, name: 'Transport', description: 'Handles shuttle and facility issues.', assigned_officer: 'transport01' },
]

const SEED_CATEGORIES: Category[] = [
  { id: 1, name: 'Hostel Room Maintenance', description: 'Plumbing, electrical, and structural repairs.', department: 'Hostel Administration', department_id: 1, documents: [SEED_DOCUMENT_TYPES[1], SEED_DOCUMENT_TYPES[2]] },
  { id: 2, name: 'Library Book Issuance', description: 'Missing or delayed library resources.', department: 'ICT', department_id: 2, documents: [SEED_DOCUMENT_TYPES[0]] },
  { id: 3, name: 'Fee Payment Receipt', description: 'Payment confirmation discrepancies.', department: 'Bursary', department_id: 3, documents: [SEED_DOCUMENT_TYPES[3]] },
  { id: 4, name: 'Transport Facility', description: 'Shuttle scheduling and access issues.', department: 'Transport', department_id: 5, documents: [SEED_DOCUMENT_TYPES[0]] },
  { id: 5, name: 'Exam Result Discrepancy', description: 'Incorrect or missing exam results.', department: 'Exams & Records', department_id: 4, documents: [SEED_DOCUMENT_TYPES[0], SEED_DOCUMENT_TYPES[5]] },
]

const SEED_USERS: UserProfile[] = [
  { id: 1, username: 'student01', email: 'john.doe@student.edu', first_name: 'John', last_name: 'Doe', role: 'student', matric_number: '2021001234', department_name: 'Computer Science', level: '300', is_active: true },
  { id: 2, username: 'rahul.kumar', email: 'rahul.kumar@student.edu', first_name: 'Rahul', last_name: 'Kumar', role: 'student', matric_number: '2021004821', department_name: 'Mechanical Engineering', level: '200', is_active: true },
  { id: 3, username: 'officer01', email: 'shomari@staff.edu', first_name: 'Rajesh', last_name: 'Sharma', role: 'hod', department_name: 'Hostel Administration', is_active: true },
  { id: 4, username: 'ict_officer01', email: 'ict.officer@staff.edu', first_name: 'Amara', last_name: 'Okafor', role: 'ict_officer', department_name: 'ICT', is_active: true },
  { id: 5, username: 'exams01', email: 'exams.officer@staff.edu', first_name: 'Grace', last_name: 'Idowu', role: 'exams_officer', department_name: 'Exams & Records', is_active: true },
  { id: 6, username: 'admin', email: 'admin@university.edu', first_name: 'System', last_name: 'Administrator', role: 'admin', is_active: true },
]

const KEYS = {
  departments: 'sims.mock.departments',
  categories: 'sims.mock.categories',
  documentTypes: 'sims.mock.document_types',
  users: 'sims.mock.users',
}

// ---------------------------------------------------------------------------
// Departments
// ---------------------------------------------------------------------------

export async function listDepartments(): Promise<Department[]> {
  await wait()
  return load(KEYS.departments, SEED_DEPARTMENTS)
}

export async function saveDepartment(dept: Omit<Department, 'id'> & { id?: number }): Promise<Department> {
  await wait()
  const all = load(KEYS.departments, SEED_DEPARTMENTS)
  if (dept.id) {
    const idx = all.findIndex((d) => d.id === dept.id)
    if (idx >= 0) all[idx] = { ...all[idx], ...dept, id: dept.id }
    save(KEYS.departments, all)
    return all[idx]
  }
  const created: Department = { ...dept, id: Math.max(0, ...all.map((d) => d.id)) + 1 }
  all.push(created)
  save(KEYS.departments, all)
  return created
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export async function listCategories(): Promise<Category[]> {
  await wait()
  return load(KEYS.categories, SEED_CATEGORIES)
}

export async function saveCategory(cat: Omit<Category, 'id'> & { id?: number }): Promise<Category> {
  await wait()
  const all = load(KEYS.categories, SEED_CATEGORIES)
  if (cat.id) {
    const idx = all.findIndex((c) => c.id === cat.id)
    if (idx >= 0) all[idx] = { ...all[idx], ...cat, id: cat.id }
    save(KEYS.categories, all)
    return all[idx]
  }
  const created: Category = { ...cat, id: Math.max(0, ...all.map((c) => c.id)) + 1 }
  all.push(created)
  save(KEYS.categories, all)
  return created
}

// ---------------------------------------------------------------------------
// Document types
// ---------------------------------------------------------------------------

export async function listDocumentTypes(): Promise<DocumentType[]> {
  await wait()
  return load(KEYS.documentTypes, SEED_DOCUMENT_TYPES)
}

export async function saveDocumentType(doc: Omit<DocumentType, 'id'> & { id?: number }): Promise<DocumentType> {
  await wait()
  const all = load(KEYS.documentTypes, SEED_DOCUMENT_TYPES)
  if (doc.id) {
    const idx = all.findIndex((d) => d.id === doc.id)
    if (idx >= 0) all[idx] = { ...all[idx], ...doc, id: doc.id }
    save(KEYS.documentTypes, all)
    return all[idx]
  }
  const created: DocumentType = { ...doc, id: Math.max(0, ...all.map((d) => d.id)) + 1 }
  all.push(created)
  save(KEYS.documentTypes, all)
  return created
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export async function listUsers(): Promise<UserProfile[]> {
  await wait()
  return load(KEYS.users, SEED_USERS)
}

export async function saveUser(
  user: Omit<UserProfile, 'id'> & { id?: number },
): Promise<UserProfile> {
  await wait()
  const all = load(KEYS.users, SEED_USERS)
  if (user.id) {
    const idx = all.findIndex((u) => u.id === user.id)
    if (idx >= 0) all[idx] = { ...all[idx], ...user, id: user.id }
    save(KEYS.users, all)
    return all[idx]
  }
  const created: UserProfile = { ...user, id: Math.max(0, ...all.map((u) => u.id)) + 1, is_active: true }
  all.push(created)
  save(KEYS.users, all)
  return created
}

export async function setUserActive(id: number, isActive: boolean): Promise<void> {
  await wait()
  const all = load(KEYS.users, SEED_USERS)
  const idx = all.findIndex((u) => u.id === id)
  if (idx >= 0) {
    all[idx].is_active = isActive
    save(KEYS.users, all)
  }
}

// Derived from the shared Role vocabulary (types/index.ts) rather than a
// second hardcoded list, so this mock module's "Filter by role" dropdown
// (admin/Users.tsx) never drifts out of sync with the real role set again.
export const ALL_ROLES: Role[] = ['student', ...STAFF_ROLES]
