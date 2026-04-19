// ChatWindow.jsx — Scrollable message list
// FIXED: suggested questions are clickable
// Auto scrolls to bottom when new message arrives

import { useEffect, useRef } from 'react'
import { Bot, Sparkles } from 'lucide-react'
import ChatMessage from './ChatMessage'
import Loader from '../ui/Loader'

const ChatWindow = ({
  messages,
  loading,
  onSend,    // passed from ChatPage so suggestions can send
}) => {
  const bottomRef = useRef(null)
  const safeMessages = Array.isArray(messages) ? messages : []

  // Auto scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [safeMessages, loading])

  // Suggested starter questions
  const SUGGESTIONS = [
    'What are the main topics in my documents?',
    'Summarize the key points',
    'What does the research say about this topic?',
  ]

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">

      {/* ── Welcome screen (empty chat) ───────────── */}
      {safeMessages.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center h-full space-y-4 py-12">

          {/* Bot icon */}
          <div className="
            w-16 h-16 rounded-2xl
            bg-dark-700 border border-dark-500
            flex items-center justify-center
          ">
            <Bot size={28} className="text-neon-purple" />
          </div>

          {/* Title and description */}
          <div className="text-center">
            <h3 className="text-white font-semibold text-lg">
              AI Knowledge Assistant
            </h3>
            <p className="text-slate-500 text-sm mt-1 max-w-sm">
              Ask me anything about your uploaded documents.
              I'll find the most relevant information for you.
            </p>
          </div>

          {/* Clickable suggested questions */}
          <div className="flex flex-col gap-2 w-full max-w-sm mt-4">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => typeof onSend === 'function' && onSend(suggestion)}
                className="
                  flex items-center gap-2 p-3
                  bg-dark-700 rounded-xl
                  border border-dark-500
                  hover:border-neon-purple
                  hover:bg-dark-600
                  text-slate-400 hover:text-white
                  text-sm text-left
                  cursor-pointer
                  transition-all duration-200
                  w-full
                "
              >
                <Sparkles size={13} className="text-neon-purple flex-shrink-0" />
                {suggestion}
              </button>
            ))}
          </div>

        </div>
      )}

      {/* ── Messages list ─────────────────────────── */}
      {safeMessages.map((message, index) => (
        <ChatMessage
          key={message?.id ?? `msg-${index}`}
          message={message}
        />
      ))}

      {/* ── AI thinking indicator ─────────────────── */}
      {loading && (
        <div className="flex gap-3 items-center">
          <div className="
            w-8 h-8 rounded-xl
            bg-dark-600 border border-dark-500
            flex items-center justify-center
          ">
            <Bot size={15} className="text-neon-purple" />
          </div>
          <div className="
            px-4 py-3 rounded-2xl rounded-tl-sm
            bg-dark-700 border border-dark-500
          ">
            <div className="flex items-center gap-2">
              <Loader size="sm" />
              <span className="text-slate-500 text-sm">Thinking...</span>
            </div>
          </div>
        </div>
      )}

      {/* Scroll anchor — always at bottom */}
      <div ref={bottomRef} />

    </div>
  )
}

export default ChatWindow