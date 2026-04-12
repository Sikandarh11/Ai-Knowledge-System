// chat.js — Multi-turn chat API call
// Adapts backend /chat response shape to frontend chat UI expectations.

import axiosInstance from './axiosInstance'

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