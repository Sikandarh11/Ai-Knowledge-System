// ChatInput.jsx — Message input bar at bottom of chat
// Features:
//   - Text input with Enter to send
//   - Shift+Enter for new line
//   - Disabled while AI is thinking
//   - Send button with loading state
//
// 🔌 BACKEND: onSend triggers POST /chat

import { useEffect, useRef, useState } from 'react'
import { Loader, Mic, Send, Square } from 'lucide-react'
import toast from 'react-hot-toast'

const ChatInput = ({
  onSend,      // function called with message string
  onVoiceRecorded,
  prefillText = '',
  prefillNonce = 0,
  disabled,    // true while waiting for AI response
  placeholder = 'Ask anything about your documents...'
}) => {
  const [message, setMessage] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isVoiceBusy, setIsVoiceBusy] = useState(false)
  const textareaRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  useEffect(() => {
    if (!prefillText || typeof prefillText !== 'string') {
      return
    }

    setMessage(prefillText)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
      textareaRef.current.focus()
    }
  }, [prefillText, prefillNonce])

  // ─── Handle send ──────────────────────────────────
  const handleSend = () => {
    const trimmed = message.trim()
    if (!trimmed || disabled) return

    onSend(trimmed)    // pass message to parent
    setMessage('')     // clear input

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  // ─── Handle keyboard ──────────────────────────────
  const handleKeyDown = (e) => {
    // Enter = send, Shift+Enter = new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ─── Auto resize textarea ─────────────────────────
  // Grows as user types multiple lines
  const handleChange = (e) => {
    setMessage(e.target.value)
    // Reset height then set to scrollHeight
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
  }

  const stopActiveStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }

  const startRecording = async () => {
    if (disabled || isVoiceBusy) {
      return
    }

    if (!navigator?.mediaDevices?.getUserMedia || typeof window.MediaRecorder === 'undefined') {
      toast.error('Voice recording is not supported in this browser')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const preferredType = window.MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : ''

      const recorder = preferredType
        ? new MediaRecorder(stream, { mimeType: preferredType })
        : new MediaRecorder(stream)

      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onstop = async () => {
        try {
          const blobType = recorder.mimeType || 'audio/webm'
          const audioBlob = new Blob(chunksRef.current, { type: blobType })
          chunksRef.current = []

          if (audioBlob.size === 0) {
            toast.error('No audio captured. Please try again.')
            return
          }

          if (typeof onVoiceRecorded === 'function') {
            const extension = blobType.includes('webm') ? 'webm' : 'wav'
            await onVoiceRecorded(audioBlob, {
              filename: `voice-message-${Date.now()}.${extension}`,
            })
          }
        } catch {
          toast.error('Failed to process recorded audio')
        } finally {
          stopActiveStream()
          setIsVoiceBusy(false)
        }
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
    } catch {
      stopActiveStream()
      toast.error('Microphone access denied or unavailable')
    }
  }

  const stopRecording = () => {
    if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') {
      return
    }
    setIsRecording(false)
    setIsVoiceBusy(true)
    mediaRecorderRef.current.stop()
  }

  const handleVoiceToggle = async () => {
    if (isRecording) {
      stopRecording()
      return
    }
    await startRecording()
  }

  return (
    <div className="
      flex items-end gap-3 p-4
      bg-dark-800
      border-t border-dark-500
    ">

      {/* ── Text input ────────────────────────────── */}
      <div className="
        flex-1
        bg-dark-700
        border border-dark-500
        focus-within:border-neon-purple
        rounded-2xl
        px-4 py-3
        transition-colors duration-200
      ">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="
            w-full bg-transparent
            text-white text-sm
            placeholder-slate-600
            outline-none resize-none
            leading-relaxed
            disabled:opacity-50
          "
          style={{ maxHeight: '120px' }}
        />
      </div>

      <button
        onClick={handleVoiceToggle}
        disabled={disabled || isVoiceBusy}
        className={`
          w-11 h-11 rounded-2xl flex-shrink-0
          flex items-center justify-center
          transition-all duration-200
          ${isRecording
            ? 'bg-red-500 hover:bg-red-600 text-white cursor-pointer'
            : disabled || isVoiceBusy
            ? 'bg-dark-600 border border-dark-500 text-slate-600 cursor-not-allowed'
            : 'bg-dark-700 hover:border-neon-cyan border border-dark-500 text-neon-cyan cursor-pointer'
          }
        `}
        title={isRecording ? 'Stop recording' : 'Record voice message'}
      >
        {isVoiceBusy
          ? <Loader size={16} className="animate-spin text-neon-cyan" />
          : isRecording
          ? <Square size={16} />
          : <Mic size={16} />
        }
      </button>

      {/* ── Send button ───────────────────────────── */}
      {/* 🔌 BACKEND: triggers POST /chat on click */}
      <button
        onClick={handleSend}
        disabled={!message.trim() || disabled}
        className={`
          w-11 h-11 rounded-2xl flex-shrink-0
          flex items-center justify-center
          transition-all duration-200
          ${message.trim() && !disabled
            ? 'bg-neon-purple hover:bg-purple-600 shadow-neon-sm text-white cursor-pointer'
            : 'bg-dark-600 border border-dark-500 text-slate-600 cursor-not-allowed'
          }
        `}
      >
        {disabled
          ? <Loader size={16} className="animate-spin text-neon-purple" />
          : <Send size={16} />
        }
      </button>

    </div>
  )
}

export default ChatInput