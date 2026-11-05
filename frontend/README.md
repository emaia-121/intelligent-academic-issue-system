# Student Issue Management System — Frontend

React 19 + TypeScript + Vite + Tailwind CSS v4, built against the Django REST
backend in this repository. This README documents exactly what is wired to
the real API versus backed by a clearly-labelled mock layer, so nothing here
is presented as "real" when it isn't.

## Getting started

```bash
cd frontend
npm install
npm run dev      # starts Vite on http://localhost:5173, proxying /api -> http://localhost:8000
```

Run the Django dev server on port 8000 in parallel (`python manage.py
runserver`). To point at a different backend host, set `VITE_API_BASE_URL` in
a `.env` file (defaults to `/api`, proxied by Vite in dev).

```bash
npm run build     # tsc -b && vite build -> dist/
npm run preview   # serve the production build locally
```

## What's real vs. mock

The backend (verified by reading the Django project directly, not assumed)
only implements JWT auth and the issue lifecycle. Everything else the
reference designs call for has no endpoint yet. Rather than fabricate data
that looks real, this app calls the genuine API wherever it exists and
isolates everything else behind an explicitly-labelled mock layer
(`src/api/mock/`) that's trivial to delete once the real endpoints ship.

**Live-wired to the real Django API:**
- Login (`POST /api/token/`, refresh via `POST /api/token/refresh/`)
- Create Issue (`POST /api/issues/create/`)
- My Issues / Assigned Issues / All Issues (`GET /api/issues/`)
- Issue Detail, activity history, status timeline (`GET /api/issues/:id/`)
- Document upload (`POST /api/issues/:id/upload-document/`)
- Status updates, including the resolution-notes-required rule and the
  backend's exact allowed-transition graph (`PATCH /api/issues/:id/status/`)
- Notifications (built by aggregating each user's real issue activity —
  there's no notifications endpoint, but every entry shown is real)
- Reports (status breakdown, trend line, and department stats are computed
  from the real issues list; only total-user/department counts fall back to
  mock data, since accounts/departments have no list endpoint)

**Mock-only (`src/api/mock/`, `localStorage`-backed, heavily commented in
code) because the backend app exists but has no wired-up view/URL yet:**
- User registration and management
- Department, Category, and Document Type management
- The authenticated user's full profile (name, matric number, department) —
  login only returns a JWT, so the role is confirmed via a visible selector
  on the login screen rather than guessed
- Forgot/reset password

Fields the reference designs show but the backend doesn't track at all
(e.g. issue priority) render as `—` (see `NotTracked` in
`src/components/ui/StatusBadge.tsx`) instead of an invented value.

## Route map

| Path | Role | Notes |
| --- | --- | --- |
| `/`, `/login`, `/register`, `/forgot-password` | Public | |
| `/student/dashboard`, `/issues/new`, `/issues`, `/issues/:id`, `/issues/:id/documents`, `/track`, `/notifications`, `/profile` | Student | |
| `/staff/dashboard`, `/issues`, `/all-issues`, `/issues/:id`, `/reports`, `/profile` | Staff (course adviser, HOD, ICT/exams officer) | |
| `/admin/dashboard`, `/users`, `/departments`, `/categories`, `/documents`, `/reports`, `/settings`, `/audit-logs` | Admin | `/settings` and `/audit-logs` are explicit "coming soon" placeholders — they appear in the reference mockups with no backing spec or model |

## Project structure

```
src/
  api/            real API clients (client.ts, auth.ts, issues.ts) + api/mock/ (clearly labelled)
  components/
    layout/       AppShell, Sidebar, Topbar
    ui/           shared primitives (StatusBadge, DataTable, FormField, DocumentUploadWidget, ...)
  context/        AuthContext
  routes/         ProtectedRoute / RoleRoute guards
  pages/          auth/, student/, staff/, admin/, issues/ (shared detail page), reports/, profile/
  lib/            format.ts, timeline.ts, documentChecklist.ts
  types/          the full type contract, with a MOCK-ONLY section marked in comments
```
