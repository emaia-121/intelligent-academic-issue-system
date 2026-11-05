import { apiClient } from './client'
import type { Department } from '@/types'

export async function listDepartments(): Promise<Department[]> {
  const res = await apiClient.get<Department[]>('/departments/')
  return res.data
}