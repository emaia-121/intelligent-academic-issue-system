import { Link } from 'react-router-dom'
import { GraduationCap, FilePlus2, Search, ShieldCheck, ArrowRight } from 'lucide-react'

const FEATURES = [
  {
    icon: FilePlus2,
    title: 'Submit issues in minutes',
    description: 'Pick a category, describe the problem, and attach the exact documents required.',
  },
  {
    icon: Search,
    title: 'Track every step',
    description: 'Follow your issue from submission to resolution with a live status timeline.',
  },
  {
    icon: ShieldCheck,
    title: 'Role-based access',
    description: 'Students, staff, and administrators each get a workspace built for their role.',
  },
]

export function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-brand-600 text-white">
            <GraduationCap className="size-5" />
          </div>
          <span className="text-lg font-bold text-slate-900">SIMS</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm font-semibold text-slate-600 hover:text-slate-900">
            Sign in
          </Link>
          <Link
            to="/register"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Get started
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20 pt-12 sm:pt-20">
        <div className="mx-auto max-w-2xl text-center">
          <span className="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
            Student Issue Management System
          </span>
          <h1 className="mt-5 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Every campus issue, tracked from report to resolution
          </h1>
          <p className="mt-4 text-lg text-slate-500">
            One platform for students to raise issues, staff to resolve them, and administrators
            to keep everything organized.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/register"
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700 sm:w-auto"
            >
              Create an account
              <ArrowRight className="size-4" />
            </Link>
            <Link
              to="/login"
              className="flex w-full items-center justify-center rounded-lg border border-slate-200 px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 sm:w-auto"
            >
              I already have an account
            </Link>
          </div>
        </div>

        <div className="mt-20 grid gap-6 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div key={title} className="card p-6">
              <div className="flex size-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <Icon className="size-5" />
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
              <p className="mt-1.5 text-sm text-slate-500">{description}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-slate-100 py-6 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} Student Issue Management System
      </footer>
    </div>
  )
}
