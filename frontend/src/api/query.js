// query.js — RAG query API call
// This is the core feature — asking questions about documents
//
// DUMMY DATA: returns a fake AI answer right now
// 🔌 BACKEND: replace with real POST /query call

import axiosInstance from './axiosInstance'

// ─── DUMMY DATA ───────────────────────────────────
// 🔌 BACKEND: delete this when connecting
const DUMMY_ANSWERS = [
  "Based on the documents in your workspace, the main topic covers advanced machine learning techniques including neural networks and deep learning architectures.",
  "The document discusses three key points: data preprocessing, model training, and evaluation metrics for measuring performance.",
  "According to the uploaded research paper, the proposed method achieves 94% accuracy on the benchmark dataset.",
]
// ── END DUMMY DATA ─────────────────────────────────


// ─── QUERY documents with a question ─────────────
// Backend endpoint: POST /query
// Body: { workspace_id: 1, query: "What is this about?" }
// Returns: { answer: "...", sources: [...] }
export const queryDocuments = async (workspaceId, question) => {
  // ── DUMMY VERSION ─────────────────────────────────
  await new Promise(resolve => setTimeout(resolve, 1500)) // simulate AI thinking
  const randomAnswer = DUMMY_ANSWERS[Math.floor(Math.random() * DUMMY_ANSWERS.length)]
  return {
    answer: randomAnswer,
    sources: [
      { filename: 'research.pdf',  chunk_index: 3, relevance: 0.92 },
      { filename: 'notes.docx',    chunk_index: 1, relevance: 0.87 },
    ]
  }

  // 🔌 BACKEND: delete dummy code above, uncomment below:
  // const response = await axiosInstance.post('/query', {
  //   workspace_id: workspaceId,
  //   query: question,
  // })
  // return response.data
}