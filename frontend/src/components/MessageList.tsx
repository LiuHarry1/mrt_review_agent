import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatTurn } from '../types'

interface MessageListProps {
  history: ChatTurn[]
  loading?: boolean
  messagesEndRef?: React.RefObject<HTMLDivElement | null>
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
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="20 6 11 15 7 11" />
                            </svg>
                          ) : (
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                fill="currentColor"
                                fillRule="evenodd"
                                clipRule="evenodd"
                                d="M21 3.5V17a2 2 0 0 1-2 2h-2v-2h2V3.5H9v2h5.857c1.184 0 2.143.895 2.143 2v13c0 1.105-.96 2-2.143 2H5.143C3.959 22.5 3 21.605 3 20.5v-13c0-1.105.96-2 2.143-2H7v-2a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2m-6.143 4H5.143v13h9.714z"
                              />
                            </svg>
                          )}
                        </button>
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'up' ? 'active' : ''}`}
                          onClick={() => handleFeedback('up', index)}
                          title="Thumbs up"
                        >
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill="currentColor"
                              fillRule="evenodd"
                              clipRule="evenodd"
                              d="M9 10.395V20.5h8.557a1 1 0 0 0 .98-.797l1.774-8.576A.937.937 0 0 0 19.393 10h-3.659a2.177 2.177 0 0 1-2.093-2.775L14.678 3.6a.736.736 0 0 0-1.342-.576zM7 11v9.5H5a1 1 0 0 1-1-1V12a1 1 0 0 1 1-1zM5 9a3 3 0 0 0-3 3v7.5a3 3 0 0 0 3 3h12.557a3 3 0 0 0 2.938-2.392l1.774-8.576A2.937 2.937 0 0 0 19.393 8h-3.659a.177.177 0 0 1-.17-.225l1.037-3.627a2.736 2.736 0 0 0-4.989-2.139L7.5 9z"
                            />
                          </svg>
                        </button>
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'down' ? 'active' : ''}`}
                          onClick={() => handleFeedback('down', index)}
                          title="Thumbs down"
                        >
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill="currentColor"
                              fillRule="evenodd"
                              clipRule="evenodd"
                              d="M15 13.605V3.5H6.443a1 1 0 0 0-.98.797L3.69 12.873A.937.937 0 0 0 4.607 14h3.659a2.177 2.177 0 0 1 2.093 2.775l-1.037 3.627a.736.736 0 0 0 1.342.575zM17 13V3.5h2a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1zm2 2a3 3 0 0 0 3-3V4.5a3 3 0 0 0-3-3H6.443a3 3 0 0 0-2.938 2.392l-1.774 8.576A2.937 2.937 0 0 0 4.607 16h3.659c.117 0 .202.112.17.225l-1.037 3.627a2.736 2.736 0 0 0 4.989 2.139L16.5 15z"
                            />
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
      {/* Scroll anchor at bottom for newest messages */}
      <div ref={messagesEndRef} className="chat-scroll-anchor" />
    </div>
  )
}

