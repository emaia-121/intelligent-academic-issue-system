import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { SelectField, TextField, TextAreaField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Loading'
import { createIssue } from '@/api/issues'
import { getCategories } from '@/api/categories'
import { extractErrorMessage } from '@/api/client'
import type { CategoryOption, PredictedCategory } from '@/types'

/**
 * The student only ever supplies title + description. Category is
 * determined by the ML classifier on the backend (CreateIssueAPIView),
 * never chosen up front. Manual category selection is an *exception*
 * path, not the normal flow -- it only happens if the classifier asks
 * for confirmation (medium confidence) and the student rejects its guess,
 * or the classifier reports it can't confidently determine a category
 * (low confidence). Confidence itself is never shown to the student; this
 * component only ever branches on the `status` the backend returns.
 */
type Stage =
  | { name: 'form' }
  | { name: 'confirm'; predicted: PredictedCategory }
  | { name: 'manual'; reason: 'rejected' | 'low_confidence' }

export function CreateIssue() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [stage, setStage] = useState<Stage>({ name: 'form' })
  const [categories, setCategories] = useState<CategoryOption[] | null>(null)
  const [categoryId, setCategoryId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const finishCreate = async (chosenCategoryId?: number) => {
    setError(null)
    setIsSubmitting(true)
    try {
      const result = await createIssue({
        title,
        description,
        category_id: chosenCategoryId,
      })

      if (result.status === 'created') {
        navigate(`/student/issues/${result.issue_id}/documents`, {
          state: { requiredDocuments: result.required_documents },
        })
        return
      }

      if (result.status === 'confirmation_required') {
        setStage({ name: 'confirm', predicted: result.predicted_category })
        return
      }

      // manual_selection_required
      setStage({ name: 'manual', reason: 'low_confidence' })
      if (!categories) {
        const list = await getCategories()
        setCategories(list)
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not submit your issue. Please try again.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    finishCreate()
  }

  const handleConfirm = () => {
    if (stage.name !== 'confirm') return
    finishCreate(stage.predicted.id)
  }

  const handleReject = async () => {
    setStage({ name: 'manual', reason: 'rejected' })
    if (!categories) {
      const list = await getCategories()
      setCategories(list)
    }
  }

  const handleManualSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!categoryId) {
      setError('Please select a category.')
      return
    }
    finishCreate(Number(categoryId))
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Create an Issue" description="Tell us what's wrong and we'll route it to the right team." />

      {stage.name === 'form' && (
        <form className="card space-y-5 p-6" onSubmit={handleSubmit}>
          {error && <Alert variant="error">{error}</Alert>}

          <TextField
            label="Title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief summary of the issue"
            maxLength={150}
          />

          <TextAreaField
            label="Description"
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the issue in detail — what happened, when, and where."
            rows={6}
          />

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70 sm:w-auto sm:px-8"
          >
            {isSubmitting && <Spinner className="size-4 text-white" />}
            Submit Issue
          </button>
        </form>
      )}

      {stage.name === 'confirm' && (
        <div className="card space-y-5 p-6">
          {error && <Alert variant="error">{error}</Alert>}

          <div>
            <p className="text-sm text-slate-600">We think your issue is:</p>
            <p className="mt-1 text-lg font-semibold text-slate-800">{stage.predicted.name}</p>
            <p className="mt-3 text-sm text-slate-600">Is this correct?</p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isSubmitting}
              className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70"
            >
              {isSubmitting && <Spinner className="size-4 text-white" />}
              Yes, that's correct
            </button>
            <button
              type="button"
              onClick={handleReject}
              disabled={isSubmitting}
              className="flex h-11 flex-1 items-center justify-center rounded-lg border border-slate-200 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-70"
            >
              No, let me choose
            </button>
          </div>
        </div>
      )}

      {stage.name === 'manual' && (
        <form className="card space-y-5 p-6" onSubmit={handleManualSubmit}>
          {error && <Alert variant="error">{error}</Alert>}

          <p className="text-sm text-slate-600">
            {stage.reason === 'low_confidence'
              ? "We couldn't confidently determine the category for this issue. Please select one."
              : 'Please select the correct category for this issue.'}
          </p>

          <SelectField
            label="Category"
            required
            placeholder={categories === null ? 'Loading categories…' : 'Select a category'}
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            disabled={categories === null}
            options={(categories ?? []).map((c) => ({ value: String(c.id), label: `${c.name} · ${c.department}` }))}
          />

          <button
            type="submit"
            disabled={isSubmitting || categories === null}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-70 sm:w-auto sm:px-8"
          >
            {isSubmitting && <Spinner className="size-4 text-white" />}
            Submit Issue
          </button>
        </form>
      )}
    </div>
  )
}
