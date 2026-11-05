import type { IssueDocumentRecord, RequiredDocumentChecklistItem } from '@/types'
import type { RequiredDocSlot } from '@/components/ui/DocumentUploadWidget'

/**
 * Merges a category's required-document list with an issue's actually-
 * uploaded documents to produce the slot list DocumentUploadWidget/
 * IssueDetail render.
 *
 * Both real backend responses that carry a required-document list use the
 * exact same {document_id, document_name} shape (RequiredDocumentChecklistItem):
 *   - POST /api/issues/create/ -- CreateIssueResult.required_documents,
 *     available immediately after creation.
 *   - GET /api/issues/:id/ -- IssueDetailSerializer.required_documents,
 *     available whenever an existing issue is reopened later (My Issues,
 *     Assigned Issues, All Issues). Backed by Category.required_documents()
 *     (categories/models.py) on the backend -- see issues/serializers.py.
 *
 * This function is now pure and synchronous: both callers already have
 * real data in hand, so there is nothing left to fetch here. It no longer
 * falls back to the mock category catalogue (src/api/mock/store.ts),
 * which never matched the real, canonical category names and silently
 * produced an empty checklist for every issue reopened after creation.
 */
export function buildDocumentChecklist(
  requiredDocuments: RequiredDocumentChecklistItem[],
  uploadedDocs: IssueDocumentRecord[],
): RequiredDocSlot[] {
  return requiredDocuments.map((doc) => ({
    document_id: doc.document_id,
    document_name: doc.document_name,
    uploaded: uploadedDocs.find((d) => d.document === doc.document_name),
  }))
}
