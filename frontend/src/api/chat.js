// chat.js — Multi-turn chat API call
// Like query but maintains conversation history
//
// DUMMY DATA: returns fake responses right now
// 🔌 BACKEND: replace with real POST /chat call

import axiosInstance from './axiosInstance'

// ─── DUMMY DATA ───────────────────────────────────
// 🔌 BACKEND: delete this when connecting
const DUMMY_RESPONSES = [
  "I found relevant information in your documents. The content suggests that this topic has multiple dimensions worth exploring further.",
  "Based on what I can see in your knowledge base, there are 3 documents that relate to your question. Would you like me to summarize them?",
  "Great question! According to the uploaded files, the answer involves several key concepts that are interconnected.",
  "I've analyzed your documents and found that this is covered in detail in research.pdf, specifically in the methodology section.",
]
// ── END DUMMY DATA ─────────────────────────────────


// ─── SEND a chat message ──────────────────────────
// Backend endpoint: POST /chat
// Body: { workspace_id: 1, message: "...", history: [...] }
// Returns: { response: "...", sources: [...] }
export const sendChatMessage = async (workspaceId, message, history = []) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 1200)) // simulate AI response time
  const randomResponse = DUMMY_RESPONSES[Math.floor(Math.random() * DUMMY_RESPONSES.length)]
  return {
    response: randomResponse,
    sources: [
      { filename: 'research.pdf', chunk_index: 2, relevance: 0.89 },
    ]
  }

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.post('/chat', {
  //   workspace_id: workspaceId,
  //   message,
  //   history,
  // })
  // return response.data
}