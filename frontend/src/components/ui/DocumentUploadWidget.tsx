import { useRef, useState } from 'react'
import { CheckCircle2, FileText, RefreshCw, UploadCloud } from 'lucide-react'
import clsx from 'clsx'
import { Spinner } from './Loading'
import type { IssueDocumentRecord } from '@/types'
import { formatRelative } from '@/lib/format'

export interface RequiredDocSlot {
  document_id: number
  document_name: string
  uploaded?: IssueDocumentRecord
}

function fileNameFromPath(path: string): string {
  const parts = path.split('/')
  return parts[parts.length - 1] || path
}

function DocumentSlot({
  slot,
  onUpload,
  isUploading,
}: {
  slot: RequiredDocSlot
  onUpload: (documentId: number, file: File) => void
  isUploading: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const isUploaded = !!slot.uploaded

  return (
    <div
      className={clsx(
        'rounded-xl border-2 border-dashed p-4 transition-colors',
        isUploaded ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200 hover:border-brand-300',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-800">
            {slot.document_name} <span className="text-red-500">*</span>
          </p>
          {isUploaded ? (
            <p className="mt-1 flex items-center gap-1 truncate text-xs text-emerald-700">
              <CheckCircle2 className="size-3.5 shrink-0" />
              {fileNameFromPath(slot.uploaded!.file)} · {formatRelative(slot.uploaded!.uploaded_at)}
            </p>
          ) : (
            <p className="mt-1 text-xs text-slate-500">Upload clear photo or scan showing this document.</p>
          )}
        </div>
        <div
          className={clsx(
            'flex size-9 shrink-0 items-center justify-center rounded-lg',
            isUploaded ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400',
          )}
        >
          <FileText className="size-4" />
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onUpload(slot.document_id, file)
          e.target.value = ''
        }}
      />

      <button
        type="button"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
        className={clsx(
          'mt-3 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60',
          isUploaded ? 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50' : 'bg-brand-600 text-white hover:bg-brand-700',
        )}
      >
        {isUploading ? (
          <Spinner className="size-3.5" />
        ) : isUploaded ? (
          <RefreshCw className="size-3.5" />
        ) : (
          <UploadCloud className="size-3.5" />
        )}
        {isUploaded ? 'Replace file' : 'Upload'}
      </button>
    </div>
  )
}

export function DocumentUploadWidget({
  slots,
  onUpload,
  uploadingId,
}: {
  slots: RequiredDocSlot[]
  onUpload: (documentId: number, file: File) => void
  uploadingId?: number | null
}) {
  const [error, setError] = useState<string | null>(null)

  const handleUpload = (documentId: number, file: File) => {
    setError(null)
    const maxBytes = 10 * 1024 * 1024
    if (file.size > maxBytes) {
      setError('File is larger than the 10MB limit per document.')
      return
    }
    onUpload(documentId, file)
  }

  const uploadedCount = slots.filter((s) => s.uploaded).length

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          {uploadedCount} of {slots.length} required documents uploaded
        </span>
        <div className="h-1.5 w-32 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${slots.length ? (uploadedCount / slots.length) * 100 : 0}%` }}
          />
        </div>
      </div>

      {error && <p className="text-xs font-medium text-red-600">{error}</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        {slots.map((slot) => (
          <DocumentSlot
            key={slot.document_id}
            slot={slot}
            onUpload={handleUpload}
            isUploading={uploadingId === slot.document_id}
          />
        ))}
      </div>
    </div>
  )
}
