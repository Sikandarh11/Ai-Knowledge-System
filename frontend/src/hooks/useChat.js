// useChat.js — Custom hook managing chat state
// Handles per-workspace chat history
// Keeps ChatPage.jsx clean
//
// Usage:
// const { messages, send, clear, loading } = useChat(workspaceId)
// 🔌 BACKEND: send() calls POST /chat

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { clearChatHistory, getChatHistory, sendChatMessage } from '../api/chat'

const normalizeHistoryMessage = (message) => ({
  id: message.id,
  role: message.role,
  content: message.content,
  sources: message.sources || [],
  timestamp: message.created_at ? new Date(message.created_at) : new Date(),
})

const buildCacheKey = (userId) => `chat_histories:${userId || 'anonymous'}`

const readCachedHistories = (userId) => {
  if (typeof window === 'undefined') {
    return {}
  }

  try {
    const raw = sessionStorage.getItem(buildCacheKey(userId))
    if (!raw) {
      return {}
    }

    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

const writeCachedHistories = (userId, histories) => {
  if (typeof window === 'undefined') {
    return
  }

  try {
    sessionStorage.setItem(buildCacheKey(userId), JSON.stringify(histories))
  } catch {
    // Cache failures should never block chat.
  }
}

const useChat = (workspaceId, userId = null) => {

  // Stores chat history per workspace
  // { workspaceId: [messages] }
  // 🔌 BACKEND: when connecting, can load history from
  //    GET /chat/history?workspace_id={id}
  const [chatHistories, setChatHistories] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setChatHistories(readCachedHistories(userId))
  }, [userId])

  useEffect(() => {
    writeCachedHistories(userId, chatHistories)
  }, [userId, chatHistories])

  useEffect(() => {
    const loadWorkspaceHistory = async () => {
      if (!workspaceId) {
        return
      }

      const cachedHistories = readCachedHistories(userId)
      if (cachedHistories[workspaceId]) {
        setChatHistories(prev => ({
          ...prev,
          [workspaceId]: cachedHistories[workspaceId],
        }))
      }

      try {
        const history = await getChatHistory(workspaceId)
        setChatHistories(prev => ({
          ...prev,
          [workspaceId]: history.map(normalizeHistoryMessage),
        }))
      } catch {
        // Keep local state if backend history cannot be loaded.
        if (!chatHistories[workspaceId]) {
          setChatHistories(prev => ({
            ...prev,
            [workspaceId]: [],
          }))
        }
      }
    }

    loadWorkspaceHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId])

  // Messages for current workspace
  const messages = chatHistories[workspaceId] || []

  // ── Add message to workspace history ─────────────
  const addMessage = (wsId, message) => {
    setChatHistories(prev => ({
      ...prev,
      [wsId]: [...(prev[wsId] || []), message],
    }))
  }

  // ── Send message ──────────────────────────────────
  // 🔌 BACKEND: POST /chat { workspace_id, message, history }
  const send = async (text) => {
    if (!workspaceId) {
      toast.error('No chat target selected')
      return
    }

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    addMessage(workspaceId, userMessage)
    setLoading(true)

    try {
      // Build history for context
      // 🔌 BACKEND: history enables multi-turn conversation
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
      }))

      // 🔌 BACKEND: POST /chat
      const response = await sendChatMessage(workspaceId, text, history)

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date(),
      }
      addMessage(workspaceId, assistantMessage)

    } catch (err) {
      addMessage(workspaceId, {
        id: Date.now() + 1,
        role: 'error',
        content: 'Something went wrong. Please try again.',
        timestamp: new Date(),
      })
      toast.error('Failed to get response')
    } finally {
      setLoading(false)
    }
  }

  // ── Clear current workspace chat ──────────────────
  const clear = async () => {
    if (workspaceId) {
      try {
        await clearChatHistory(workspaceId)
      } catch {
        toast.error('Failed to clear chat history on server')
      }
    }

    setChatHistories(prev => ({
      ...prev,
      [workspaceId]: [],
    }))
  }

  // ── Get message count per workspace ──────────────
  const getMessageCount = (wsId) => {
    return chatHistories[wsId]?.length || 0
  }

  return {
    messages,         // current workspace messages
    loading,          // true while waiting for AI
    send,             // send a message
    clear,            // clear current chat
    getMessageCount,  // message count per workspace
    chatHistories,    // all histories (for dropdown counts)
  }
}

export default useChat