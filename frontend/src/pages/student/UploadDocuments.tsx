import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Alert } from '@/components/ui/Alert'
import { PageLoader } from '@/components/ui/Loading'
import { DocumentUploadWidget, type RequiredDocSlot } from '@/components/ui/DocumentUploadWidget'
import { getIssue, uploadIssueDocument } from '@/api/issues'
import { buildDocumentChecklist } from '@/lib/documentChecklist'
import { extractErrorMessage } from '@/api/client'
import type { RequiredDocumentChecklistItem } from '@/types'

export function UploadDocuments() {
  const { id } = useParams<{ id: string }>()
  const issueId = Number(id)
  const location = useLocation()

  const [slots, setSlots] = useState<RequiredDocSlot[] | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [uploadingId, setUploadingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const freshRequiredDocs = (location.state as { requiredDocuments?: RequiredDocumentChecklistItem[] } | null)
    ?.requiredDocuments

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (freshRequiredDocs) {
        if (!cancelled) {
          setSlots(freshRequiredDocs.map((d) => ({ document_id: d.document_id, document_name: d.document_name })))
        }
        return
      }
      try {
        const issue = await getIssue(issueId)
        const checklist = buildDocumentChecklist(issue.required_documents, issue.documents)
        if (!cancelled) {
          setSlots(checklist)
          setIsComplete(issue.is_complete)
        }
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load this issue.'))
      }
    }

    load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issueId])

  const handleUpload = async (documentId: number, file: File) => {
    setError(null)
    setUploadingId(documentId)
    try {
      const result = await uploadIssueDocument(issueId, documentId, file)
      setIsComplete(result.is_complete)
      setSlots((prev) =>
        prev
          ? prev.map((slot) =>
              slot.document_id === documentId
                ? {
                    ...slot,
                    uploaded: {
                      id: Date.now(),
                      document: slot.document_name,
                      file: file.name,
                      uploaded_at: new Date().toISOString(),
                    },
                  }
                : slot,
            )
          : prev,
      )
    } catch (err) {
      setError(extractErrorMessage(err, 'Upload failed. Please try again.'))
    } finally {
      setUploadingId(null)
    }
  }

  if (error && !slots) {
    return (
      <div className="mx-auto max-w-2xl">
        <Alert variant="error">{error}</Alert>
      </div>
    )
  }

  if (!slots) return <PageLoader label="Loading required documents…" />

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Upload Documents"
        description={`Required documents for issue #${issueId.toString().padStart(4, '0')}.`}
      />

      {error && (
        <div className="mb-4">
          <Alert variant="error">{error}</Alert>
        </div>
      )}

      <div className="card p-6">
        {isComplete && (
          <div className="mb-5 flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            <CheckCircle2 className="size-4.5 shrink-0" />
            All required documents received. Your issue has moved to review.
          </div>
        )}

        <DocumentUploadWidget slots={slots} onUpload={handleUpload} uploadingId={uploadingId} />

        <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-5">
          <Link to="/student/issues" className="text-sm font-semibold text-slate-500 hover:text-slate-700">
            Skip for now
          </Link>
          <Link
            to={`/student/issues/${issueId}`}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            View Issue
          </Link>
        </div>
      </div>
    </div>
  )
}
