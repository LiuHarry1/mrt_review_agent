import { useState, useEffect, useRef } from 'react'
import type { ChatResponse, Suggestion, Alert } from '../types'
import { sendChatMessageStream } from '../api'
import { useChatSessions } from './useChatSessions'

export function useChat() {
  const { activeSession, updateActiveSession, createSession } = useChatSessions()

  const [sessionId, setSessionId] = useState<string | undefined>(activeSession?.sessionId)
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<ChatResponse['history']>(activeSession?.history ?? [])
  const [suggestions, setSuggestions] = useState<Suggestion[] | undefined>(activeSession?.suggestions)
  const [summary] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<Alert | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Sync local state when active session changes
  useEffect(() => {
    if (!activeSession) {
      // Use setTimeout to defer state update until after render
      setTimeout(() => {
        createSession()
      }, 0)
      return
    }
    setSessionId(activeSession.sessionId)
    setHistory(activeSession.history)
    setSuggestions(activeSession.suggestions)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSession])

  const sendMessage = async (text?: string, files?: Array<{ name: string; content: string }>) => {
    const messageText = text || message.trim()

    if (!messageText && (!files || files.length === 0)) {
      setAlert({ type: 'error', message: 'Please enter content to send or upload a file.' })
      return
    }

    // Validate file sizes (already validated in useFileUpload, but double-check)
    if (files && files.length > 0) {
      const oversizedFiles = files.filter((f) => {
        let size = new Blob([f.content]).size
        if (f.content.startsWith('[BINARY_FILE:')) {
          const base64Content = f.content.split(':')[2]?.split(']')[0] || ''
          size = Math.floor(base64Content.length * 0.75)
        }
        return size > 5 * 1024 * 1024
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

    const userMessageContent =
      messageText || (files && files.length > 0 ? files.map((f) => `[文件: ${f.name}]`).join(', ') : '')

    const currentHistory = userMessageContent
      ? [...history, { role: 'user', content: messageText || userMessageContent }]
      : history

    if (userMessageContent) {
      setHistory(currentHistory)
      // Derive chat title from the first user message if not already set
      if (!activeSession?.title || activeSession.title === 'New chat' || activeSession.title === 'New conversation') {
        const rawTitle = (messageText || userMessageContent).replace(/\s+/g, ' ').trim()
        const newTitle = rawTitle.slice(0, 30) || 'New chat'
        updateActiveSession({ title: newTitle, history: currentHistory })
      } else {
        updateActiveSession({ history: currentHistory })
      }
    }

    setLoading(true)

    let assistantMessageIndex = -1
    if (userMessageContent) {
      const updatedHistory = [...currentHistory, { role: 'assistant', content: '' }]
      assistantMessageIndex = updatedHistory.length - 1
      setHistory(updatedHistory)
      updateActiveSession({ history: updatedHistory })
    }

    try {
      const payload = {
        session_id: sessionId,
        message: messageText || undefined,
        files,
        messages: currentHistory.map((turn) => ({
          role: turn.role,
          content: turn.content,
        })),
      }

      let accumulatedContent = ''
      let currentSessionId = sessionId || undefined

      await sendChatMessageStream(
        payload,
        (chunk: string) => {
          accumulatedContent += chunk
          setHistory((prev) => {
            const updated = [...prev]
            if (assistantMessageIndex >= 0 && assistantMessageIndex < updated.length) {
              updated[assistantMessageIndex] = {
                role: 'assistant',
                content: accumulatedContent,
              }
            } else if (assistantMessageIndex < 0 && accumulatedContent) {
              updated.push({ role: 'assistant', content: accumulatedContent })
              assistantMessageIndex = updated.length - 1
            }
            updateActiveSession({ history: updated })
            return updated
          })
        },
        () => {
          setLoading(false)
          if (currentSessionId) {
            setSessionId(currentSessionId)
            updateActiveSession({ sessionId: currentSessionId })
          }
        },
        (error: string) => {
          setLoading(false)
          if (userMessageContent) {
            setHistory(history)
            setMessage(messageText)
          }
          setAlert({ type: 'error', message: error })
        },
      )

      if (accumulatedContent && assistantMessageIndex >= 0) {
        const finalHistory = [...currentHistory, { role: 'assistant', content: accumulatedContent }]
        updateActiveSession({
          history: finalHistory,
          suggestions: undefined,
          summary: undefined,
        })
      }
    } catch (error) {
      setLoading(false)
      if (userMessageContent) {
        setHistory(history)
        setMessage(messageText)
      }
      const errorMessage = error instanceof Error ? error.message : 'Send failed'
      setAlert({ type: 'error', message: errorMessage })
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
    alert,
    setAlert,
    messagesEndRef,
    sendMessage,
  }
}

