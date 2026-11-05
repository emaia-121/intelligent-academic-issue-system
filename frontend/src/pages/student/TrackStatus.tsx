import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { getIssue } from '@/api/issues'

/** Extracts a numeric issue id from either a raw number or a reference
 * string like "#ISSUE-2026-0004" (see lib/format.ts's issueRef()). */
function parseIssueId(raw: string): number | null {
  const value = raw.trim()

  // Accept a formatted reference such as #ISSUE-2026-0004.
  const referenceMatch = value.match(/^#?ISSUE-\d{4}-(\d+)$/i)

  if (referenceMatch) {
    const id = Number(referenceMatch[1])
    return Number.isFinite(id) && id > 0 ? id : null
  }

  // Also accept a plain numeric issue ID such as 4.
  const id = Number(value)

  return Number.isInteger(id) && id > 0 ? id : null
}

export function TrackStatus() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    const id = parseIssueId(query)
    if (!id) {
      setError('Enter a valid issue ID or reference, e.g. #ISSUE-2026-0004.')
      return
    }

    setIsSearching(true)
    try {
      const issue = await getIssue(id)
      navigate(`/student/issues/${issue.id}`)
    } catch {
      setError(`No issue found matching "${query}".`)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Track Status" description="Look up any issue by its ID or reference number." />

      <form className="card p-6" onSubmit={handleSubmit}>
        {error && (
          <div className="mb-4">
            <Alert variant="error">{error}</Alert>
          </div>
        )}

        <label htmlFor="track-query" className="mb-1.5 block text-sm font-medium text-slate-700">
          Issue ID or reference
        </label>
        <div className="flex gap-2">
          <input
            id="track-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="#ISSUE-2026-0004"
            className="h-11 flex-1 rounded-lg border border-slate-200 bg-white px-3.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
          <button
            type="submit"
            disabled={isSearching}
            className="flex h-11 shrink-0 items-center gap-1.5 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-70"
          >
            {isSearching ? <Spinner className="size-4 text-white" /> : <Search className="size-4" />}
            Track
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          You can find your issue's reference number on its detail page or in My Issues.
        </p>
      </form>
    </div>
  )
}
