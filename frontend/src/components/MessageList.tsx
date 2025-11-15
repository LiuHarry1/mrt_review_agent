import ReactMarkdown from 'react-markdown'
import type { ChatTurn } from '../types'

interface MessageListProps {
  history: ChatTurn[]
  loading?: boolean
  messagesEndRef?: React.RefObject<HTMLDivElement>
}

export function MessageList({ history, loading, messagesEndRef }: MessageListProps) {
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

  return (
    <div className="chat-messages">
      {history.map((turn, index) => {
        const isLastMessage = index === history.length - 1
        const isAssistantLoading = isLastMessage && turn.role === 'assistant' && loading && !turn.content
        
        // Skip rendering if it's an empty assistant message (will show typing indicator separately)
        if (isAssistantLoading) {
          return null
        }
        
        return (
          <div key={`${turn.role}-${index}`} className={`message-wrapper ${turn.role}`}>
            <div className="message-content">
              <div className="message-bubble">
                {turn.role === 'assistant' ? (
                  turn.content ? (
                    <ReactMarkdown>{turn.content}</ReactMarkdown>
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

