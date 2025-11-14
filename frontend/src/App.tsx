import { useEffect, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { reviewMrt, sendChatMessage } from './api'
import type { ChatResponse, ConversationState, ChecklistItem, ReviewResponse, Suggestion } from './types'
import { ChecklistEditorModal } from './ChecklistEditorModal'

type TabKey = 'review' | 'chat'

type Alert = { type: 'error' | 'success'; message: string }

const CHAT_STORAGE_KEY = 'mrt-review-chat-session'

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('review')
  const [sidebarVisible, setSidebarVisible] = useState(true)

  const [mrtContent, setMrtContent] = useState('')
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewAlert, setReviewAlert] = useState<Alert | null>(null)
  const [isChecklistModalOpen, setIsChecklistModalOpen] = useState(false)
  const [customSystemPrompt, setCustomSystemPrompt] = useState<string | undefined>(undefined)
  const [customChecklist, setCustomChecklist] = useState<ChecklistItem[] | undefined>(undefined)

  const [chatSessionId, setChatSessionId] = useState<string | undefined>()
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatResponse['history']>([])
  const [chatSuggestions, setChatSuggestions] = useState<Suggestion[] | undefined>()
  const [chatSummary, setChatSummary] = useState<string | undefined>()
  const [chatLoading, setChatLoading] = useState(false)
  const [chatAlert, setChatAlert] = useState<Alert | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const stored = window.localStorage.getItem(CHAT_STORAGE_KEY)
    if (!stored) return
    try {
      const parsed = JSON.parse(stored) as {
        sessionId?: string
        state?: ConversationState
        history?: ChatResponse['history']
        suggestions?: Suggestion[]
        summary?: string
      }
      if (parsed.sessionId && parsed.history && parsed.state) {
        setChatSessionId(parsed.sessionId)
        setChatHistory(parsed.history)
        setChatSuggestions(parsed.suggestions)
        setChatSummary(parsed.summary)
      }
    } catch (error) {
      console.warn('Failed to restore chat session', error)
      window.localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const adjustHeight = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }

    adjustHeight()
    textarea.addEventListener('input', adjustHeight)
    return () => textarea.removeEventListener('input', adjustHeight)
  }, [chatMessage])

  // Auto scroll to bottom when messages update
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatHistory, chatLoading])

  const handleReviewSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setReviewAlert(null)
    setReviewResult(null)
    setReviewLoading(true)

    try {
      const payload = {
        mrt_content: mrtContent,
        checklist: customChecklist,
        system_prompt: customSystemPrompt,
      }

      const response = await reviewMrt(payload)
      setReviewResult(response)
      setReviewAlert({ type: 'success', message: 'Review completed' })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Review failed'
      setReviewAlert({ type: 'error', message })
    } finally {
      setReviewLoading(false)
    }
  }

  const handleChecklistSave = (systemPrompt: string, checklist: ChecklistItem[]) => {
    setCustomSystemPrompt(systemPrompt)
    setCustomChecklist(checklist)
  }

  const persistChat = (response: ChatResponse) => {
    if (typeof window === 'undefined') return
    const payload = {
      sessionId: response.session_id,
      state: response.state,
      history: response.history,
      suggestions: response.suggestions,
      summary: response.summary,
    }
    window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(payload))
  }

  const handleFilesUpload = async () => {
    if (uploadedFiles.length === 0) return

    setChatAlert(null)
    setChatLoading(true)

    try {
      // Maximum file size: 1MB per file
      const MAX_FILE_SIZE = 1024 * 1024 // 1MB
      const oversizedFiles = uploadedFiles.filter(file => file.size > MAX_FILE_SIZE)
      if (oversizedFiles.length > 0) {
        const fileNames = oversizedFiles.map(f => f.name).join(', ')
        setChatAlert({ 
          type: 'error', 
          message: `File too large (over 1MB): ${fileNames}. Please upload smaller files.` 
        })
        setChatLoading(false)
        return
      }

      // Read all files
      const filesData = await Promise.all(
        uploadedFiles.map(async (file) => {
          try {
            const content = await file.text()
            return { name: file.name, content }
          } catch (error) {
            throw new Error(`Failed to read file ${file.name}: ${error instanceof Error ? error.message : 'Unknown error'}`)
          }
        })
      )

      const payload = {
        session_id: chatSessionId,
        message: chatMessage.trim() || undefined,
        files: filesData,
      }

      const response = await sendChatMessage(payload)
      setChatSessionId(response.session_id)
      setChatHistory(response.history)
      setChatSuggestions(response.suggestions)
      setChatSummary(response.summary)
      setChatMessage('')
      setUploadedFiles([])
      persistChat(response)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'File upload failed'
      setChatAlert({ type: 'error', message })
    } finally {
      setChatLoading(false)
    }
  }

  const handleChatSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    
    // If there are uploaded files, handle file upload
    if (uploadedFiles.length > 0) {
      await handleFilesUpload()
      return
    }

    if (!chatMessage.trim()) {
      setChatAlert({ type: 'error', message: 'Please enter content to send or upload a file.' })
      return
    }

    setChatAlert(null)
    setChatLoading(true)

    try {
      const payload = {
        session_id: chatSessionId,
        message: chatMessage.trim(),
      }
      const response = await sendChatMessage(payload)
      setChatSessionId(response.session_id)
      setChatHistory(response.history)
      setChatSuggestions(response.suggestions)
      setChatSummary(response.summary)
      setChatMessage('')
      persistChat(response)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Send failed'
      setChatAlert({ type: 'error', message })
    } finally {
      setChatLoading(false)
    }
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    const validExtensions = ['.txt', '.md', '.json', '.text']
    const MAX_FILE_SIZE = 1024 * 1024 // 1MB
    
    const textFiles = files.filter((file) => {
      const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      const isValidType = validExtensions.includes(fileExtension) || file.type.startsWith('text/')
      const isValidSize = file.size <= MAX_FILE_SIZE
      return isValidType && isValidSize
    })

    const oversizedFiles = files.filter(file => file.size > MAX_FILE_SIZE)
    const invalidTypeFiles = files.filter(file => {
      const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      return !validExtensions.includes(fileExtension) && !file.type.startsWith('text/')
    })

    if (textFiles.length > 0) {
      setUploadedFiles((prev) => [...prev, ...textFiles])
      if (oversizedFiles.length > 0 || invalidTypeFiles.length > 0) {
        const warnings = []
        if (oversizedFiles.length > 0) {
          warnings.push(`File too large (>1MB): ${oversizedFiles.map(f => f.name).join(', ')}`)
        }
        if (invalidTypeFiles.length > 0) {
          warnings.push(`Unsupported file format: ${invalidTypeFiles.map(f => f.name).join(', ')}`)
        }
        setChatAlert({ type: 'error', message: warnings.join('; ') })
      }
    } else if (files.length > 0) {
      const reasons = []
      if (oversizedFiles.length > 0) {
        reasons.push('File too large (over 1MB)')
      }
      if (invalidTypeFiles.length > 0) {
        reasons.push('Unsupported file format')
      }
      setChatAlert({ type: 'error', message: `File validation failed: ${reasons.join(', ')}. Only text files are supported: .txt, .md, .json, each file not exceeding 1MB.` })
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      const fileArray = Array.from(files)
      const validExtensions = ['.txt', '.md', '.json', '.text']
      const MAX_FILE_SIZE = 1024 * 1024 // 1MB
      
      const textFiles = fileArray.filter((file) => {
        const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
        const isValidType = validExtensions.includes(fileExtension) || file.type.startsWith('text/')
        const isValidSize = file.size <= MAX_FILE_SIZE
        return isValidType && isValidSize
      })

      const oversizedFiles = fileArray.filter(file => file.size > MAX_FILE_SIZE)
      const invalidTypeFiles = fileArray.filter(file => {
        const fileExtension = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
        return !validExtensions.includes(fileExtension) && !file.type.startsWith('text/')
      })

      if (textFiles.length > 0) {
        setUploadedFiles((prev) => [...prev, ...textFiles])
        if (oversizedFiles.length > 0 || invalidTypeFiles.length > 0) {
          const warnings = []
          if (oversizedFiles.length > 0) {
            warnings.push(`File too large (>1MB): ${oversizedFiles.map(f => f.name).join(', ')}`)
          }
          if (invalidTypeFiles.length > 0) {
            warnings.push(`Unsupported file format: ${invalidTypeFiles.map(f => f.name).join(', ')}`)
          }
          setChatAlert({ type: 'error', message: warnings.join('; ') })
        }
      } else {
        const reasons = []
        if (oversizedFiles.length > 0) {
          reasons.push('File too large (over 1MB)')
        }
        if (invalidTypeFiles.length > 0) {
          reasons.push('Unsupported file format')
        }
        setChatAlert({ type: 'error', message: `File validation failed: ${reasons.join(', ')}. Only text files are supported: .txt, .md, .json, each file not exceeding 1MB.` })
      }
    }
    // Reset input to allow selecting same file again
    if (e.target) {
      e.target.value = ''
    }
  }

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const resetChatSession = () => {
    setChatSessionId(undefined)
    setChatHistory([])
    setChatSuggestions(undefined)
    setChatSummary(undefined)
    setChatAlert(null)
    setChatMessage('')
    setUploadedFiles([])
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }


  return (
    <div className="app">
      {/* Top Bar */}
      <header className={`top-bar ${sidebarVisible ? 'with-sidebar' : 'no-sidebar'}`}>
        <div className="top-bar-left">
          {!sidebarVisible && (
            <button
              type="button"
              className="sidebar-toggle-top"
              onClick={() => setSidebarVisible(true)}
              title="Show menu"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          )}
          {activeTab === 'chat' && (
            <button type="button" className="new-chat-btn-top" onClick={resetChatSession}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              <span>New Chat</span>
            </button>
          )}
        </div>
        <div className="top-bar-right">
          <div className="user-info">
            <div className="user-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <div className="user-details">
              <span className="user-name">Dummy User</span>
              <span className="user-role">Test Reviewer</span>
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarVisible ? 'visible' : 'hidden'}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="brand-logo">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </div>
            <div className="brand-name">MRT Review Agent</div>
          </div>
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={() => setSidebarVisible(false)}
            title="Hide menu"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <nav className="sidebar-nav">
          <button
            type="button"
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <span className="nav-text">Chat Review</span>
          </button>
          <button
            type="button"
            className={`nav-item ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => setActiveTab('review')}
          >
            <span className="nav-text">Quick Review</span>
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${sidebarVisible ? 'with-sidebar' : 'no-sidebar'}`}>
        {activeTab === 'review' && (
          <section className="review-container">
            <div className="review-header">
              <div className="review-header-top">
                <div className="review-title-section">
                  <h2>Quick Review</h2>
                  <p className="review-subtitle">
                    Get instant AI-powered review results. Paste your MRT content and receive comprehensive feedback.
                  </p>
                </div>
                <button
                  type="button"
                  className="edit-checklist-btn"
                  onClick={() => setIsChecklistModalOpen(true)}
                  title="Edit Checklist and System Prompt"
                >
                  <span>Configure</span>
                </button>
              </div>
            </div>
            <form onSubmit={handleReviewSubmit} className="review-form">
              <div className="form-group">
                <label className="form-label">
                  <span className="label-text">MRT Test Case</span>
                  <span className="label-required">*</span>
                </label>
                <textarea
                  required
                  value={mrtContent}
                  onChange={(event) => setMrtContent(event.target.value)}
                  placeholder="Paste your complete MRT test case content here..."
                  className="form-textarea"
                />
                <p className="form-hint">The AI will review your test case against the configured checklist and provide improvement suggestions.</p>
              </div>

              <div className="form-actions">
                <button type="submit" disabled={reviewLoading} className="submit-button">
                  {reviewLoading ? (
                    <>
                      <div className="loading-spinner small"></div>
                      <span>Reviewing...</span>
                    </>
                  ) : (
                    <>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 11l3 3L22 4" />
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                      </svg>
                      <span>Start Review</span>
                    </>
                  )}
                </button>
              </div>

              {reviewAlert && (
                <div className={`alert-message ${reviewAlert.type}`}>
                  {reviewAlert.message}
                </div>
              )}

              {reviewResult && (
                <div className="review-results">
                  <div className="result-markdown">
                    <ReactMarkdown>
                      {reviewResult.raw_content || reviewResult.summary || 'No content available'}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </form>

            <ChecklistEditorModal
              isOpen={isChecklistModalOpen}
              onClose={() => setIsChecklistModalOpen(false)}
              onSave={handleChecklistSave}
              initialSystemPrompt={customSystemPrompt}
              initialChecklist={customChecklist}
            />
          </section>
        )}

        {activeTab === 'chat' && (
          <section className="chat-container">
            {/* Chat Messages Area */}
            <div className="chat-messages-wrapper">
              {chatHistory.length === 0 ? (
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
              ) : (
                <div className="chat-messages">
                  {chatHistory.map((turn, index) => (
                    <div key={`${turn.role}-${index}`} className={`message-wrapper ${turn.role}`}>
                      <div className="message-content">
                        <div className="message-bubble">
                          {turn.role === 'assistant' ? (
                            <ReactMarkdown>{turn.content}</ReactMarkdown>
                          ) : (
                            <div style={{ whiteSpace: 'pre-wrap' }}>{turn.content}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
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
              )}

              {(chatSummary || (chatSuggestions && chatSuggestions.length > 0)) && chatHistory.length > 0 && (
                <div className="chat-results">
                  <div className="result-markdown">
                    <ReactMarkdown>
                      {`${chatSummary ? `## Review Summary\n\n${chatSummary}\n\n` : ''}${chatSuggestions && chatSuggestions.length > 0
                        ? `## Improvement Suggestions (${chatSuggestions.length})\n\n${chatSuggestions
                            .map((item) => `- **${item.checklist_id}**: ${item.message}`)
                            .join('\n')}\n`
                        : ''}`}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>

            {/* Chat Input Area */}
            <div
              className={`chat-input-container ${isDragOver ? 'drag-over' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {uploadedFiles.length > 0 && (
                <div className="files-preview-container">
                  {uploadedFiles.map((file, index) => (
                    <div key={index} className="file-preview-bar">
                      <div className="file-info">
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">
                          {(file.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="file-remove-btn"
                        title="Remove file"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <form onSubmit={handleChatSubmit} className="chat-input-form">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                  accept=".txt,.md,.json,.text"
                  multiple
                />
                <div className="chat-input-wrapper">
                  <textarea
                    ref={textareaRef}
                    value={chatMessage}
                    onChange={(event) => setChatMessage(event.target.value)}
                    placeholder={
                      isDragOver
                        ? 'Release to upload file...'
                        : 'Enter message or drag and drop file to upload...'
                    }
                    rows={3}
                    className="chat-textarea"
                    disabled={chatLoading}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        if (!chatLoading && (chatMessage.trim() || uploadedFiles.length > 0)) {
                          handleChatSubmit(e as any)
                        }
                      }
                    }}
                  />
                  <div className="chat-input-actions">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="attach-button"
                      title="Upload file"
                      disabled={chatLoading}
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                      </svg>
                    </button>
                    <button
                      type="submit"
                      disabled={chatLoading || (!chatMessage.trim() && uploadedFiles.length === 0)}
                      className="send-button"
                      title="Send (Enter)"
                    >
                      {chatLoading ? (
                        <div className="loading-spinner"></div>
                      ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="22" y1="2" x2="11" y2="13"></line>
                          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
                {chatAlert && (
                  <div className={`alert-toast ${chatAlert.type}`}>
                    {chatAlert.message}
                  </div>
                )}
              </form>
              {isDragOver && (
                <div className="drag-overlay">
                  <div className="drag-overlay-inner">
                    <p className="drag-text">Release to upload file</p>
                    <p className="drag-hint">Processed as MRT file by default</p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
