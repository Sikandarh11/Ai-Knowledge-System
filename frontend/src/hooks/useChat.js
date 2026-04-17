// useChat.js — Custom hook managing chat state
// Handles per-workspace chat history
// Keeps ChatPage.jsx clean
//
// Usage:
// const { messages, send, clear, loading } = useChat(workspaceId)
// 🔌 BACKEND: send() calls POST /chat

import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { clearChatHistory, getChatHistory, sendChatMessage, sendChatMessageStream } from '../api/chat'

const normalizeHistoryMessage = (message) => ({
  id: message.id,
  role: message.role,
  content: message.content,
  sources: message.sources || [],
  timestamp: message.created_at ? new Date(message.created_at) : new Date(),
})

const normalizeMessageList = (value) => {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((message) => {
    return (
      message
      && typeof message === 'object'
      && typeof message.role === 'string'
      && typeof message.content === 'string'
    )
  })
}

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
    if (!parsed || typeof parsed !== 'object') {
      return {}
    }

    return Object.entries(parsed).reduce((acc, [key, value]) => {
      acc[key] = normalizeMessageList(value)
      return acc
    }, {})
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
    let cancelled = false

    const loadWorkspaceHistory = async () => {
      if (!workspaceId) {
        return
      }

      const cachedHistories = readCachedHistories(userId)
      if (!cancelled && cachedHistories[workspaceId]) {
        setChatHistories(prev => ({
          ...prev,
          [workspaceId]: normalizeMessageList(cachedHistories[workspaceId]),
        }))
      }

      try {
        const history = await getChatHistory(workspaceId)
        if (cancelled) {
          return
        }
        setChatHistories(prev => ({
          ...prev,
          [workspaceId]: normalizeMessageList(history.map(normalizeHistoryMessage)),
        }))
      } catch {
        if (cancelled) {
          return
        }
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

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId])

  // Messages for current workspace
  const messages = normalizeMessageList(chatHistories[workspaceId])

  // ── Add message to workspace history ─────────────
  const addMessage = (wsId, message) => {
    setChatHistories(prev => ({
      ...prev,
      [wsId]: [...normalizeMessageList(prev[wsId]), message],
    }))
  }

  const updateMessage = (wsId, messageId, patch) => {
    setChatHistories((prev) => {
      const existing = normalizeMessageList(prev[wsId])
      return {
        ...prev,
        [wsId]: existing.map((message) => {
          if (message.id !== messageId) {
            return message
          }
          return {
            ...message,
            ...patch,
          }
        }),
      }
    })
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
    const assistantMessageId = Date.now() + 1
    addMessage(workspaceId, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date(),
    })
    setLoading(true)

    try {
      // Build history for context
      // 🔌 BACKEND: history enables multi-turn conversation
      const history = [...messages, userMessage].map(m => ({
        role: m.role,
        content: m.content,
      }))

      let streamedText = ''
      try {
        const streamedResponse = await sendChatMessageStream(
          workspaceId,
          text,
          history,
          (chunk) => {
            streamedText += chunk
            updateMessage(workspaceId, assistantMessageId, {
              content: streamedText,
            })
          }
        )

        updateMessage(workspaceId, assistantMessageId, {
          content: streamedText || streamedResponse.response,
          sources: streamedResponse.sources || [],
        })
      } catch {
        // Fallback to non-streaming endpoint when streaming is unavailable.
        const response = await sendChatMessage(workspaceId, text, history)
        updateMessage(workspaceId, assistantMessageId, {
          content: response.response,
          sources: response.sources || [],
        })
      }

    } catch (err) {
      updateMessage(workspaceId, assistantMessageId, {
        role: 'error',
        content: 'Something went wrong. Please try again.',
        sources: [],
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