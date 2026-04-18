// ChatMessage.jsx — Single chat message bubble
// Handles 3 message types:
//   1. 'user' — message from user (right side)
//   2. 'assistant' — RAG answer from AI (left side)
//   3. 'error' — error message (left side, red)
//
// Also renders source documents when AI answers
//
// DUMMY DATA: receives message object as prop
// 🔌 BACKEND: message.content comes from POST /chat response
//    { type: 'answer', response: '...', sources: [...] }

import { Bot, User, FileText, AlertCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const formatMessageTimestamp = (value) => {
  if (!value) {
    return ''
  }

  const dateValue = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(dateValue.getTime())) {
    return ''
  }

  return dateValue.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

const ChatMessage = ({ message }) => {
  const safeMessage = message && typeof message === 'object' ? message : {}
  const contentText = typeof safeMessage.content === 'string' ? safeMessage.content : ''
  const sources = Array.isArray(safeMessage.sources) ? safeMessage.sources : []
  const timestampLabel = formatMessageTimestamp(safeMessage.timestamp)
  const metadata = safeMessage.metadata && typeof safeMessage.metadata === 'object'
    ? safeMessage.metadata
    : {}
  const voiceMeta = metadata.voice && typeof metadata.voice === 'object'
    ? metadata.voice
    : {}
  const isVoiceMessage = metadata.message_type === 'voice' || Boolean(voiceMeta.status)
  const voiceStatus = voiceMeta.status || ''

  // message shape:
  // {
  //   id: unique id,
  //   role: 'user' | 'assistant' | 'error',
  //   content: 'message text',
  //   sources: [{ filename, chunk_index, relevance }] (optional)
  //   timestamp: Date object
  // }

  const isUser = safeMessage.role === 'user'
  const isError = safeMessage.role === 'error'
  const showVoiceProcessing = isVoiceMessage && isUser && voiceStatus && voiceStatus !== 'sent'

  return (
    <div className={`
      flex gap-3 w-full
      ${isUser ? 'flex-row-reverse' : 'flex-row'}
    `}>

      {/* ── Avatar ────────────────────────────────── */}
      <div className={`
        w-8 h-8 rounded-xl flex-shrink-0
        flex items-center justify-center
        ${isUser
          ? 'bg-neon-purple shadow-neon-sm'
          : isError
          ? 'bg-red-500/20 border border-red-500/30'
          : 'bg-dark-600 border border-dark-500'
        }
      `}>
        {isUser
          ? <User size={15} className="text-white" />
          : isError
          ? <AlertCircle size={15} className="text-red-400" />
          : <Bot size={15} className="text-neon-purple" />
        }
      </div>

      {/* ── Message Content ───────────────────────── */}
      <div className={`
        flex flex-col gap-2
        max-w-[75%]
        ${isUser ? 'items-end' : 'items-start'}
      `}>

        {/* Message bubble */}
        <div className={`
          px-4 py-3 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? 'bg-neon-purple text-white rounded-tr-sm'
            : isError
            ? 'bg-red-500/10 border border-red-500/20 text-red-400 rounded-tl-sm'
            : 'bg-dark-700 border border-dark-500 text-slate-200 rounded-tl-sm'
          }
        `}>
          {showVoiceProcessing ? (
            <div className="space-y-1">
              <p>{contentText || 'Voice message processing...'}</p>
              <p className="text-xs text-white/75">Status: {voiceStatus}</p>
            </div>
          ) : isUser ? (
            // User messages — plain text
            <p>{contentText}</p>
          ) : (
            // AI messages — render as markdown
            // 🔌 BACKEND: message.content = response field from POST /chat
            // ReactMarkdown renders **bold**, bullet points, code blocks etc
            <ReactMarkdown
              components={{
                // Style inline code
                code: ({ children }) => (
                  <code className="
                    bg-dark-600 px-1.5 py-0.5 rounded
                    font-mono text-xs text-neon-cyan
                  ">
                    {children}
                  </code>
                ),
                // Style paragraphs
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0">{children}</p>
                ),
                // Style bullet lists
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-1 mb-2">
                    {children}
                  </ul>
                ),
                // Style bold text
                strong: ({ children }) => (
                  <strong className="text-white font-semibold">
                    {children}
                  </strong>
                ),
              }}
            >
              {contentText}
            </ReactMarkdown>
          )}
        </div>

        {/* ── Source Documents ──────────────────────
            Shows which documents the AI used to answer
            🔌 BACKEND: sources array from POST /chat response
            Shape: [{ filename, chunk_index, relevance }]
        ─────────────────────────────────────────── */}
        {sources.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {sources.map((source, index) => (
              <div
                key={index}
                className="
                  flex items-center gap-1.5
                  px-2.5 py-1 rounded-lg
                  bg-dark-600 border border-dark-500
                  hover:border-neon-purple/50
                  transition-colors duration-200
                "
              >
                <FileText size={11} className="text-neon-cyan" />
                <span className="text-slate-400 text-xs">
                  {/* 🔌 BACKEND: source.filename from ChromaDB metadata */}
                  {source.filename}
                </span>
                {/* Relevance score as percentage */}
                {/* 🔌 BACKEND: source.relevance = similarity score from vector search */}
                <span className="text-neon-cyan text-xs font-medium">
                  {Math.round(source.relevance * 100)}%
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Timestamp */}
        {timestampLabel && (
          <span className="text-slate-600 text-xs">
            {timestampLabel}
          </span>
        )}

      </div>
    </div>
  )
}

export default ChatMessage