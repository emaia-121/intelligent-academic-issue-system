import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { DataTable, type DataTableColumn } from '@/components/ui/DataTable'
import { Modal } from '@/components/ui/Modal'
import { TextField, TextAreaField } from '@/components/ui/FormField'
import { Alert } from '@/components/ui/Alert'
import { listDocumentTypes, saveDocumentType } from '@/api/mock/store'
import type { DocumentType } from '@/types'

const emptyForm = { name: '', description: '' }

export function AdminDocumentTypes() {
  const [documentTypes, setDocumentTypes] = useState<DocumentType[] | null>(null)
  const [modalDoc, setModalDoc] = useState<DocumentType | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => listDocumentTypes().then(setDocumentTypes)

  useEffect(() => {
    refresh()
  }, [])

  const openCreate = () => {
    setModalDoc(null)
    setForm(emptyForm)
    setError(null)
    setShowModal(true)
  }

  const openEdit = (doc: DocumentType) => {
    setModalDoc(doc)
    setForm({ name: doc.name, description: doc.description ?? '' })
    setError(null)
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) {
      setError('Document type name is required.')
      return
    }
    await saveDocumentType({ id: modalDoc?.id, name: form.name, description: form.description })
    setShowModal(false)
    refresh()
  }

  const columns: DataTableColumn<DocumentType>[] = [
    {
      key: 'name',
      header: 'Document Type',
      render: (d) => (
        <button onClick={() => openEdit(d)} className="text-left hover:underline">
          <p className="font-semibold text-slate-800">{d.name}</p>
        </button>
      ),
    },
    { key: 'description', header: 'Description', render: (d) => d.description || '—' },
  ]

  return (
    <div>
      <PageHeader
        title="Document Type Management"
        description="Document types required by issue categories."
        actions={
          <button
            onClick={openCreate}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            <Plus className="size-4" />
            Add Document Type
          </button>
        }
      />

      <div className="mb-4">
        <Alert variant="info">
          No document-type API exists on the backend yet. Changes here are saved locally for demonstration only.
        </Alert>
      </div>

      <DataTable
        columns={columns}
        rows={documentTypes ?? []}
        rowKey={(d) => d.id}
        isLoading={documentTypes === null}
        emptyTitle="No document types yet"
      />

      {showModal && (
        <Modal title={modalDoc ? 'Edit Document Type' : 'Add Document Type'} onClose={() => setShowModal(false)}>
          <div className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}
            <TextField label="Name" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            <TextAreaField label="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={3} />
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50">
                Cancel
              </button>
              <button onClick={handleSave} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Save
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
