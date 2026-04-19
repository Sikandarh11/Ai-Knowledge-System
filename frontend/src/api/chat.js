// chat.js — Multi-turn chat API call
// Adapts backend /chat response shape to frontend chat UI expectations.

import axiosInstance from './axiosInstance'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const toUiRelevance = (distance) => {
  if (typeof distance !== 'number' || Number.isNaN(distance)) {
    return 0
  }

  // Distance is lower-is-better. Convert to 0..1 relevance.
  if (distance >= 0 && distance <= 1) {
    return Math.max(0, 1 - distance)
  }

  return 1 / (1 + Math.max(0, distance))
}

const normalizeSource = (source, index) => {
  const fallbackName = source.document_id ? `Document ${source.document_id}` : `Source ${index + 1}`
  return {
    filename: source.filename || fallbackName,
    chunk_index: typeof source.chunk_index === 'number' ? source.chunk_index : index,
    relevance: toUiRelevance(source.distance),
  }
}


// ─── SEND a chat message ──────────────────────────
// Backend endpoint: POST /chat
// Body: { query: "...", workspace_id: "1", history: [...] }
// Returns: { response: "...", sources: [...] }
export const sendChatMessage = async (workspaceId, message, history = []) => {
  const response = await axiosInstance.post('/chat', {
    query: message,
    workspace_id: workspaceId != null ? String(workspaceId) : null,
    history,
    include_documents: false,
  })

  const payload = response.data
  return {
    response: payload.answer || '',
    sources: (payload.sources || []).map(normalizeSource),
  }
}

export const getChatHistory = async (workspaceId) => {
  const response = await axiosInstance.get('/chat/history', {
    params: { workspace_id: workspaceId != null ? String(workspaceId) : '' },
  })

  return response.data
}

export const clearChatHistory = async (workspaceId) => {
  const response = await axiosInstance.delete('/chat/history', {
    params: { workspace_id: workspaceId != null ? String(workspaceId) : '' },
  })

  return response.data
}

export const sendChatMessageStream = async (
  workspaceId,
  message,
  history = [],
  onChunk,
  options = {}
) => {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      query: message,
      workspace_id: workspaceId != null ? String(workspaceId) : null,
      history,
      include_documents: false,
    }),
    signal: options.signal,
  })

  if (!response.ok) {
    throw new Error(`Streaming failed (${response.status})`)
  }

  if (!response.body) {
    throw new Error('Streaming response body is not available')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finalPayload = null

  const parseFrame = (frame) => {
    const lines = frame.split('\n')
    const dataLines = lines
      .map(line => line.trim())
      .filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).trim())

    if (dataLines.length === 0) {
      return null
    }

    try {
      return JSON.parse(dataLines.join(''))
    } catch {
      return null
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''

    frames.forEach((frame) => {
      const event = parseFrame(frame)
      if (!event || typeof event !== 'object') {
        return
      }

      if (event.type === 'chunk' && typeof event.content === 'string') {
        if (typeof onChunk === 'function') {
          onChunk(event.content)
        }
        return
      }

      if (event.type === 'final' && event.payload && typeof event.payload === 'object') {
        finalPayload = event.payload
        return
      }

      if (event.type === 'error') {
        throw new Error(event.message || 'Streaming failed')
      }
    })
  }

  if (!finalPayload) {
    throw new Error('No final payload received from stream')
  }

  return {
    response: finalPayload.answer || '',
    sources: (finalPayload.sources || []).map(normalizeSource),
  }
}

export const uploadVoiceMessage = async (workspaceId, audioBlob, filename = 'voice-message.webm') => {
  const formData = new FormData()
  formData.append('workspace_id', workspaceId != null ? String(workspaceId) : '__global__')
  formData.append('file', audioBlob, filename)

  const response = await axiosInstance.post('/voice/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  const payload = response.data || {}
  return {
    messageId: payload?.data?.message_id,
    status: payload?.data?.voice_status || payload?.status || 'processing',
    workspaceId: payload?.data?.workspace_id,
  }
}

export const getVoiceMessageStatus = async (messageId) => {
  const response = await axiosInstance.get(`/voice/status/${messageId}`)
  const payload = response.data || {}
  const data = payload.data || {}

  return {
    messageId: data.message_id,
    status: data.status || 'unknown',
    transcript: data.transcript || '',
    error: data.error || null,
    workspaceId: data.workspace_id,
  }
}