import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatTurn } from '../types'

interface MessageListProps {
  history: ChatTurn[]
  loading?: boolean
  messagesEndRef?: React.RefObject<HTMLDivElement>
}

export function MessageList({ history, loading, messagesEndRef }: MessageListProps) {
  // Track copied and feedback state for each message by index
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({})
  const [feedbackStates, setFeedbackStates] = useState<Record<number, 'up' | 'down' | null>>({})

  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedStates(prev => ({ ...prev, [index]: true }))
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [index]: false }))
      }, 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleFeedback = (type: 'up' | 'down', index: number) => {
    setFeedbackStates(prev => ({ ...prev, [index]: type }))
    // TODO: Send feedback to backend if needed
  }

  if (history.length === 0) {
    return (
      <div className="empty-chat-state">
        <h3 className="empty-chat-title">Start a New Conversation</h3>
        <p className="empty-chat-desc">
          Upload MRT files or enter content, AI assistant will help you review
        </p>
        <div className="empty-chat-tips">
          <div className="tip-item">
            <span>Support drag and drop file upload</span>
          </div>
          <div className="tip-item">
            <span>Processed as MRT file by default</span>
          </div>
          <div className="tip-item">
            <span>Can modify and view checklist</span>
          </div>
        </div>
      </div>
    )
  }

  // Find the last assistant message
  const lastAssistantIndex = history.length - 1
  const lastTurn = history[lastAssistantIndex]
  const isLastAssistant = lastTurn?.role === 'assistant' && lastTurn?.content && !loading

  return (
    <div className="chat-messages">
      {history.map((turn, index) => {
        const isLastMessage = index === history.length - 1
        const isAssistantLoading = isLastMessage && turn.role === 'assistant' && loading && !turn.content
        
        // Skip rendering if it's an empty assistant message (will show typing indicator separately)
        if (isAssistantLoading) {
          return null
        }
        
        const isLastAssistantMessage = isLastAssistant && index === lastAssistantIndex
        const copied = copiedStates[index] || false
        const feedback = feedbackStates[index] || null
        
        return (
          <div key={`${turn.role}-${index}`} className={`message-wrapper ${turn.role} ${isLastAssistantMessage ? 'last-assistant' : ''}`}>
            <div className="message-content">
              <div className="message-bubble">
                {turn.role === 'assistant' ? (
                  turn.content ? (
                    <>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{turn.content}</ReactMarkdown>
                      <div className={`message-actions ${isLastAssistantMessage ? 'visible' : 'hidden-on-hover'}`}>
                        <button
                          className="message-action-btn copy-btn"
                          onClick={() => handleCopy(turn.content, index)}
                          title="Copy"
                        >
                          {copied ? (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                          ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                          )}
                        </button>
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'up' ? 'active' : ''}`}
                          onClick={() => handleFeedback('up', index)}
                          title="Thumbs up"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2.12-2.3l-1.38-5.7a2 2 0 0 0-2.12-1.7zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                          </svg>
                        </button>
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'down' ? 'active' : ''}`}
                          onClick={() => handleFeedback('down', index)}
                          title="Thumbs down"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2.12 2.3l1.38 5.7a2 2 0 0 0 2.12 1.7zM17 2h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
                          </svg>
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )
                ) : (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{turn.content}</div>
                )}
              </div>
            </div>
          </div>
        )
      })}
      {loading && (!history.length || history[history.length - 1]?.role !== 'assistant' || history[history.length - 1]?.content === '') && (
        <div className="message-wrapper assistant">
          <div className="message-content">
            <div className="message-bubble typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  )
}

