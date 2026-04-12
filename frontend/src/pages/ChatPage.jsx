// ChatPage.jsx — Updated to use useChat hook + AppContext
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Database, ChevronDown } from 'lucide-react'
import ChatWindow from '../components/chat/ChatWindow'
import ChatInput from '../components/chat/ChatInput'
import Loader from '../components/ui/Loader'
import { useAppContext } from '../context/AppContext'
import useChat from '../hooks/useChat'

const GLOBAL_CHAT_ID = '__global__'
const GLOBAL_CHAT_LABEL = 'Global Chat'

const ChatPage = () => {
  const [searchParams] = useSearchParams()
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)
  const [activeChatTarget, setActiveChatTarget] = useState(GLOBAL_CHAT_ID)

  // 🔌 BACKEND: workspaces from Context → GET /workspaces
  const {
    workspaces,
    workspacesLoading,
    activeWorkspace,
    setActiveWorkspace,
    currentUser,
  } = useAppContext()

  // Set active workspace from URL if provided
  useEffect(() => {
    const urlWorkspaceId = searchParams.get('workspace')
    if (urlWorkspaceId) {
      const ws = workspaces.find(w => w.id === Number(urlWorkspaceId))
      if (ws) {
        setActiveWorkspace(ws)
        setActiveChatTarget(String(ws.id))
        return
      }
    }

    const scope = (searchParams.get('scope') || '').toLowerCase()
    if (scope === 'global' || !urlWorkspaceId) {
      setActiveChatTarget(GLOBAL_CHAT_ID)
    }
  }, [searchParams, workspaces, setActiveWorkspace])

  // useChat hook manages all chat logic
  // 🔌 BACKEND: send() calls POST /chat
  const {
    messages,
    loading,
    send,
    clear,
    getMessageCount,
    chatHistories,
  } = useChat(activeChatTarget, currentUser?.id)

  if (workspacesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" text="Loading..." />
      </div>
    )
  }

  const activeWorkspaceName = activeChatTarget === GLOBAL_CHAT_ID
    ? GLOBAL_CHAT_LABEL
    : (activeWorkspace?.name || 'Select Workspace')

  const handleSelectGlobalChat = () => {
    setActiveChatTarget(GLOBAL_CHAT_ID)
    setShowWorkspaceMenu(false)
  }

  const handleSelectWorkspaceChat = (workspace) => {
    setActiveWorkspace(workspace)
    setActiveChatTarget(String(workspace.id))
    setShowWorkspaceMenu(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] -m-6">

      {/* ── Header ────────────────────────────────── */}
      <div className="
        flex items-center justify-between
        px-6 py-4 bg-dark-800
        border-b border-dark-500 flex-shrink-0
      ">
        {/* Workspace dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
            className="
              flex items-center gap-2 bg-dark-700
              rounded-xl border border-dark-500
              hover:border-neon-purple px-4 py-2.5
              transition-colors duration-200
            "
          >
            <Database size={15} className="text-neon-purple" />
            <span className="text-white text-sm font-medium">
              {activeWorkspaceName}
            </span>
            <ChevronDown
              size={14}
              className={`text-slate-500 transition-transform duration-200
                ${showWorkspaceMenu ? 'rotate-180' : ''}`}
            />
          </button>

          {showWorkspaceMenu && (
            <div className="
              absolute top-full left-0 mt-2 w-56
              rounded-xl bg-dark-700 border border-dark-500
              shadow-neon-sm z-50 overflow-hidden
            ">
              <button
                onClick={handleSelectGlobalChat}
                className={`
                  w-full flex items-center gap-3
                  px-4 py-3 text-left text-sm
                  hover:bg-dark-600 transition-colors duration-150
                  ${activeChatTarget === GLOBAL_CHAT_ID ? 'text-neon-glow' : 'text-slate-300'}
                `}
              >
                <Database size={14} className="text-neon-purple flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="truncate">{GLOBAL_CHAT_LABEL}</p>
                  {getMessageCount(GLOBAL_CHAT_ID) > 0 && (
                    <p className="text-slate-600 text-xs">
                      {getMessageCount(GLOBAL_CHAT_ID)} messages
                    </p>
                  )}
                </div>
                {activeChatTarget === GLOBAL_CHAT_ID && (
                  <div className="w-1.5 h-1.5 rounded-full bg-neon-purple" />
                )}
              </button>

              {workspaces.map(workspace => (
                <button
                  key={workspace.id}
                  onClick={() => handleSelectWorkspaceChat(workspace)}
                  className={`
                    w-full flex items-center gap-3
                    px-4 py-3 text-left text-sm
                    hover:bg-dark-600 transition-colors duration-150
                    ${activeChatTarget === String(workspace.id) ? 'text-neon-glow' : 'text-slate-300'}
                  `}
                >
                  <Database size={14} className="text-neon-purple flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="truncate">{workspace.name}</p>
                    {/* Message count per workspace */}
                    {getMessageCount(String(workspace.id)) > 0 && (
                      <p className="text-slate-600 text-xs">
                        {getMessageCount(String(workspace.id))} messages
                      </p>
                    )}
                  </div>
                  {activeChatTarget === String(workspace.id) && (
                    <div className="w-1.5 h-1.5 rounded-full bg-neon-purple" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Clear chat */}
        {messages.length > 0 && (
          <button
            onClick={clear}
            className="
              text-slate-500 hover:text-red-400 text-xs
              px-3 py-1.5 rounded-lg hover:bg-red-400/10
              border border-transparent hover:border-red-400/20
              transition-all duration-200
            "
          >
            Clear Chat
          </button>
        )}
      </div>

      {/* ── Chat Window ───────────────────────────── */}
      <ChatWindow
        messages={messages}
        loading={loading}
        onSend={send}
      />

      {/* ── Input ─────────────────────────────────── */}
      <div className="flex-shrink-0">
        <ChatInput
          onSend={send}
          disabled={loading}
          placeholder={activeChatTarget === GLOBAL_CHAT_ID
            ? 'Ask about documents across all your workspaces...'
            : `Ask about ${activeWorkspace?.name || 'your documents'}...`}
        />
      </div>
    </div>
  )
}

export default ChatPage
