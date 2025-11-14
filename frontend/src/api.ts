import type { ChatPayload, ChatResponse, ChecklistItem, ReviewPayload, ReviewResponse } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function reviewMrt(payload: ReviewPayload): Promise<ReviewResponse> {
  const response = await fetch(`${API_BASE_URL}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<ReviewResponse>(response)
}

export async function sendChatMessage(payload: ChatPayload): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/agent/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<ChatResponse>(response)
}

export interface ConfigResponse {
  system_prompt: string
  checklist: ChecklistItem[]
}

export async function getDefaultConfig(): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<ConfigResponse>(response)
}

export interface SaveConfigPayload {
  system_prompt: string
  checklist: ChecklistItem[]
}

export interface SaveConfigResponse {
  status: string
  message: string
}

export async function saveConfig(payload: SaveConfigPayload): Promise<SaveConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/config`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<SaveConfigResponse>(response)
}

