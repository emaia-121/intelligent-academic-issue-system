import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { GraduationCap, ShieldCheck, Clock, FileCheck2 } from 'lucide-react'

const HIGHLIGHTS = [
  { icon: FileCheck2, text: 'Submit and track issues from one dashboard' },
  { icon: Clock, text: 'Real-time status updates at every stage' },
  { icon: ShieldCheck, text: 'Secure, role-based access for every user' },
]

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <div className="flex min-h-screen bg-white">
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-brand-500 px-12 py-12 text-white lg:flex">
        <div className="pointer-events-none absolute inset-0 opacity-[0.15]">
          <svg width="100%" height="100%" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="340" r="140" fill="white" />
            <circle cx="380" cy="40" r="90" fill="white" />
          </svg>
        </div>

        <Link to="/" className="relative flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-white/15">
            <GraduationCap className="size-5" />
          </div>
          <span className="text-lg font-bold">SIMS</span>
        </Link>

        <div className="relative">
          <h2 className="text-3xl font-bold leading-tight">
            Student Issue Management System
          </h2>
          <p className="mt-3 max-w-sm text-sm text-brand-50/90">
            Report campus issues, upload supporting documents, and follow every
            step of the resolution process in real time.
          </p>
          <ul className="mt-8 space-y-3.5">
            {HIGHLIGHTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-brand-50/90">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/15">
                  <Icon className="size-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-brand-50/70">
          © {new Date().getFullYear()} Student Issue Management System
        </p>
      </div>

      <div className="flex w-full flex-col justify-center px-6 py-12 sm:px-12 lg:w-1/2 lg:px-20">
        <div className="mx-auto w-full max-w-sm">
          <Link to="/" className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex size-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <GraduationCap className="size-4.5" />
            </div>
            <span className="text-sm font-bold text-slate-900">SIMS</span>
          </Link>

          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>

          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  )
}
