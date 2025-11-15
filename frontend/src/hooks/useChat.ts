import { useState, useEffect, useRef } from 'react'
import type { ChatResponse, Suggestion } from '../types'
import { sendChatMessageStream } from '../api'

const CHAT_STORAGE_KEY = 'mrt-review-chat-session'

interface Alert {
  type: 'error' | 'success'
  message: string
}

export function useChat() {
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<ChatResponse['history']>([])
  const [suggestions, setSuggestions] = useState<Suggestion[] | undefined>()
  const [summary, setSummary] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<Alert | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load session from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = window.localStorage.getItem(CHAT_STORAGE_KEY)
    if (!stored) return
    try {
      const parsed = JSON.parse(stored) as {
        sessionId?: string
        history?: ChatResponse['history']
        suggestions?: Suggestion[]
        summary?: string
      }
      if (parsed.sessionId && parsed.history) {
        setSessionId(parsed.sessionId)
        setHistory(parsed.history)
        setSuggestions(parsed.suggestions)
        setSummary(parsed.summary)
      }
    } catch (error) {
      console.warn('Failed to restore chat session', error)
      window.localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }, [])

  // Auto scroll to bottom when new messages are added (newest messages at bottom, like Doubao)
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [history.length]) // Only trigger when history length changes (new message added)

  const sendMessage = async (text?: string, files?: Array<{ name: string; content: string }>) => {
    const messageText = text || message.trim()
    
    if (!messageText && (!files || files.length === 0)) {
      setAlert({ type: 'error', message: 'Please enter content to send or upload a file.' })
      return
    }

    // Validate file sizes (already validated in useFileUpload, but double-check)
    if (files && files.length > 0) {
      const oversizedFiles = files.filter((f) => {
        // For binary files encoded as base64, the size is about 33% larger
        // Check content length for base64 encoded files
        let size = new Blob([f.content]).size
        // If it's a binary file marker, estimate original size
        if (f.content.startsWith('[BINARY_FILE:')) {
          // Base64 encoding increases size by ~33%, so decode size estimate
          const base64Content = f.content.split(':')[2]?.split(']')[0] || ''
          size = Math.floor(base64Content.length * 0.75) // Approximate original size
        }
        return size > 5 * 1024 * 1024 // 5MB
      })
      if (oversizedFiles.length > 0) {
        const fileNames = oversizedFiles.map((f) => f.name).join(', ')
        setAlert({
          type: 'error',
          message: `File too large (over 5MB): ${fileNames}. Please upload smaller files.`,
        })
        return
      }
    }

    setAlert(null)
    
    // Optimistically add user message to history immediately
    const userMessageContent = messageText || (files && files.length > 0 
      ? files.map(f => `[文件: ${f.name}]`).join(', ')
      : '')
    
    // Build updated history with user message
    const currentHistory = userMessageContent
      ? [...history, { role: 'user', content: messageText || userMessageContent }]
      : history
    
    // Optimistically update history to show user message immediately
    if (userMessageContent) {
      setHistory(currentHistory)
    }
    
    // Note: Input clearing is now handled in ChatPage before calling sendMessage
    // setMessage('') is called in ChatPage.handleSubmit
    setLoading(true)

    // Add assistant message placeholder for streaming
    let assistantMessageIndex = -1
    if (userMessageContent) {
      const updatedHistory = [...currentHistory, { role: 'assistant', content: '' }]
      assistantMessageIndex = updatedHistory.length - 1
      setHistory(updatedHistory)
    }

    try {
      const payload = {
        session_id: sessionId,
        message: messageText || undefined,
        files,
        messages: currentHistory.map(turn => ({
          role: turn.role,
          content: turn.content
        }))
      }

      // Use streaming endpoint
      let accumulatedContent = ''
      let currentSessionId = sessionId || undefined
      
      await sendChatMessageStream(
        payload,
        // onChunk: handle each chunk of streaming response
        (chunk: string) => {
          accumulatedContent += chunk
          // Update the assistant message in real-time
          setHistory((prev) => {
            const updated = [...prev]
            if (assistantMessageIndex >= 0 && assistantMessageIndex < updated.length) {
              updated[assistantMessageIndex] = {
                role: 'assistant',
                content: accumulatedContent
              }
            } else if (assistantMessageIndex < 0 && accumulatedContent) {
              // If assistant message wasn't added yet, add it now
              updated.push({ role: 'assistant', content: accumulatedContent })
              assistantMessageIndex = updated.length - 1
            }
            return updated
          })
          
          // Scroll to bottom during streaming to keep new content visible (newest messages at bottom, like Doubao)
          // Always scroll to bottom during streaming so user can see the latest output
          requestAnimationFrame(() => {
            if (messagesEndRef.current) {
              messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
            }
          })
        },
        // onDone: streaming complete
        () => {
          setLoading(false)
          // Update session ID if we got one (though stream endpoint doesn't return it currently)
          if (currentSessionId) {
            setSessionId(currentSessionId)
          }
        },
        // onError: handle errors
        (error: string) => {
          setLoading(false)
          // On error, revert optimistic update
          if (userMessageContent) {
            setHistory(history)
            setMessage(messageText) // Restore message text on error
          }
          setAlert({ type: 'error', message: error })
        }
      )

      // After streaming completes, persist the session if we have accumulated content
      if (accumulatedContent && assistantMessageIndex >= 0) {
        const finalHistory = [...currentHistory, { role: 'assistant', content: accumulatedContent }]
        // Persist session (we'll need session_id from response, but for now use existing)
        if (sessionId) {
          const sessionData = {
            sessionId,
            history: finalHistory,
            suggestions: undefined,
            summary: undefined
          }
          if (typeof window !== 'undefined') {
            window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(sessionData))
          }
        }
      }
    } catch (error) {
      setLoading(false)
      // On error, revert optimistic update
      if (userMessageContent) {
        setHistory(history)
        setMessage(messageText) // Restore message text on error
      }
      const errorMessage = error instanceof Error ? error.message : 'Send failed'
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  const resetSession = () => {
    setSessionId(undefined)
    setHistory([])
    setSuggestions(undefined)
    setSummary(undefined)
    setAlert(null)
    setMessage('')
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }

  return {
    sessionId,
    message,
    setMessage,
    history,
    suggestions,
    summary,
    loading,
    setLoading,
    alert,
    setAlert,
    messagesEndRef,
    sendMessage,
    resetSession,
  }
}

