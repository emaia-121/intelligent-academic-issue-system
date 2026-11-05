import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
// In prod, set VITE_API_BASE_URL to the deployed Django host.
const baseURL = import.meta.env.VITE_API_BASE_URL ?? '/api'

const ACCESS_KEY = 'sims.access'
const REFRESH_KEY = 'sims.refresh'

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  setAccess: (access: string) => localStorage.setItem(ACCESS_KEY, access),
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const apiClient = axios.create({ baseURL })

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) return null

  try {
    const res = await axios.post(`${baseURL}/token/refresh/`, { refresh })
    const access = res.data.access as string
    tokenStorage.setAccess(access)
    return access
  } catch {
    tokenStorage.clear()
    return null
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined

    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true

      refreshPromise = refreshPromise ?? refreshAccessToken()
      const newAccess = await refreshPromise
      refreshPromise = null

      if (newAccess) {
        original.headers = original.headers ?? {}
        original.headers.Authorization = `Bearer ${newAccess}`
        return apiClient(original)
      }

      // Refresh failed -- force a re-login.
      window.dispatchEvent(new CustomEvent('sims:session-expired'))
    }

    return Promise.reject(error)
  },
)

/** Shape of the `errors` field the backend returns on validation failures. */
export interface ApiErrorShape {
  success: false
  message: string
  errors?: Record<string, string[]> | null
}

export function extractErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as ApiErrorShape | undefined
    if (data?.errors) {
      const firstField = Object.values(data.errors)[0]
      if (firstField?.[0]) return firstField[0]
    }
    if (data?.message) return data.message
  }
  return fallback
}
