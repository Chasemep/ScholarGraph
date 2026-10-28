import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    const storedApiKey = localStorage.getItem('scholargraph_gemini_key')
    if (storedApiKey && config.data && typeof config.data === 'object' && !config.data.api_key) {
      config.data = { ...config.data, api_key: storedApiKey }
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.detail ||
      error?.message ||
      'An unexpected network error occurred.'
    return Promise.reject(new Error(message))
  }
)

export async function checkSystemHealth() {
  const { data } = await apiClient.get('/health')
  return data
}

export async function fetchDocuments() {
  const { data } = await apiClient.get('/documents')
  return data
}

export async function deleteDocument(paperId) {
  const { data } = await apiClient.delete(`/documents/${encodeURIComponent(paperId)}`)
  return data
}

export async function submitQuery({ query, topK = 5, paperIds = null, apiKey = null }) {
  const { data } = await apiClient.post('/query', {
    query,
    top_k: topK,
    paper_ids: paperIds,
    api_key: apiKey,
  })
  return data
}

export function getPaperPdfUrl(paperId) {
  return `${API_BASE_URL}/documents/${encodeURIComponent(paperId)}/pdf`
}

