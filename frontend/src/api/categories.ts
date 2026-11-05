import { apiClient } from './client'
import type { ApiEnvelope, CategoryOption } from '@/types'

export async function listCategories(): Promise<CategoryOption[]> {
  const res = await apiClient.get<ApiEnvelope<CategoryOption[]>>('/categories/')

  return res.data.data ?? []
}

export async function getCategories(): Promise<CategoryOption[]> {
  return listCategories()
}