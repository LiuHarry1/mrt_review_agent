import { useEffect, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import './App.css'
import { reviewMrt, sendChatMessage } from './api'
import type { ChatResponse, ConversationState, ReviewResponse, Suggestion } from './types'

type TabKey = 'review' | 'chat'

type Alert = { type: 'error' | 'success'; message: string }

const CHAT_STORAGE_KEY = 'mrt-review-chat-session'

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('review')

  const [mrtContent, setMrtContent] = useState('')
  const [checklistRaw, setChecklistRaw] = useState('')
  const [reviewResult, setReviewResult] = useState<ReviewResponse | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewAlert, setReviewAlert] = useState<Alert | null>(null)

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

  const handleReviewSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setReviewAlert(null)
    setReviewResult(null)
    setReviewLoading(true)

    try {
      const checklist = checklistRaw.trim() ? JSON.parse(checklistRaw) : undefined
      const payload = {
        mrt_content: mrtContent,
        checklist,
      }

      const response = await reviewMrt(payload)
      setReviewResult(response)
      setReviewAlert({ type: 'success', message: '审查完成' })
    } catch (error) {
      const message = error instanceof Error ? error.message : '审查失败'
      setReviewAlert({ type: 'error', message })
    } finally {
      setReviewLoading(false)
    }
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
          message: `文件过大（超过1MB）：${fileNames}。请上传较小的文件。` 
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
            throw new Error(`读取文件 ${file.name} 失败：${error instanceof Error ? error.message : '未知错误'}`)
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
      setChatAlert({ type: 'success', message: '文件已上传并处理' })
      setChatMessage('')
      setUploadedFiles([])
      persistChat(response)
    } catch (error) {
      const message = error instanceof Error ? error.message : '文件上传失败'
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
      setChatAlert({ type: 'error', message: '请输入要发送的内容或上传文件。' })
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
      setChatAlert({ type: 'success', message: '消息已发送' })
      setChatMessage('')
      persistChat(response)
    } catch (error) {
      const message = error instanceof Error ? error.message : '发送失败'
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
          warnings.push(`文件过大（>1MB）：${oversizedFiles.map(f => f.name).join(', ')}`)
        }
        if (invalidTypeFiles.length > 0) {
          warnings.push(`不支持的文件格式：${invalidTypeFiles.map(f => f.name).join(', ')}`)
        }
        setChatAlert({ type: 'error', message: warnings.join('；') })
      }
    } else if (files.length > 0) {
      const reasons = []
      if (oversizedFiles.length > 0) {
        reasons.push('文件过大（超过1MB）')
      }
      if (invalidTypeFiles.length > 0) {
        reasons.push('不支持的文件格式')
      }
      setChatAlert({ type: 'error', message: `文件验证失败：${reasons.join('，')}。只支持文本文件：.txt, .md, .json，每个文件不超过1MB。` })
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
            warnings.push(`文件过大（>1MB）：${oversizedFiles.map(f => f.name).join(', ')}`)
          }
          if (invalidTypeFiles.length > 0) {
            warnings.push(`不支持的文件格式：${invalidTypeFiles.map(f => f.name).join(', ')}`)
          }
          setChatAlert({ type: 'error', message: warnings.join('；') })
        }
      } else {
        const reasons = []
        if (oversizedFiles.length > 0) {
          reasons.push('文件过大（超过1MB）')
        }
        if (invalidTypeFiles.length > 0) {
          reasons.push('不支持的文件格式')
        }
        setChatAlert({ type: 'error', message: `文件验证失败：${reasons.join('，')}。只支持文本文件：.txt, .md, .json，每个文件不超过1MB。` })
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

  const renderSuggestions = (suggestions: Suggestion[]) => (
    <ul className="suggestions">
      {suggestions.map((item) => (
        <li key={`${item.checklist_id}-${item.message}`}>
          <strong>{item.checklist_id}</strong>
          <span>{item.message}</span>
        </li>
      ))}
    </ul>
  )

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="app-title">MRT Review Agent</h1>
        </div>
        <nav className="sidebar-nav">
          <button
            type="button"
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <span className="nav-icon">💬</span>
            <span className="nav-text">智能对话</span>
          </button>
          <button
            type="button"
            className={`nav-item ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => setActiveTab('review')}
          >
            <span className="nav-icon">📋</span>
            <span className="nav-text">传统审查</span>
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {activeTab === 'review' && (
          <section className="review-container">
            <div className="review-header">
              <h2>传统审查模式</h2>
              <p className="review-subtitle">一次性提交 MRT 内容和 Checklist 进行审查</p>
            </div>
            <form onSubmit={handleReviewSubmit} className="review-form">
              <div className="form-group">
                <label className="form-label">
                  <span className="label-text">MRT 内容</span>
                  <span className="label-required">*</span>
                </label>
                <textarea
                  required
                  value={mrtContent}
                  onChange={(event) => setMrtContent(event.target.value)}
                  placeholder="请粘贴完整的 MRT 测试用例..."
                  className="form-textarea"
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <span className="label-text">自定义 Checklist</span>
                  <span className="label-optional">(可选，JSON 数组格式)</span>
                </label>
                <textarea
                  value={checklistRaw}
                  onChange={(event) => setChecklistRaw(event.target.value)}
                  placeholder='[{"id":"CHK-001","description":"..."}]'
                  className="form-textarea"
                />
              </div>

              <button type="submit" disabled={reviewLoading} className="submit-button">
                {reviewLoading ? (
                  <>
                    <div className="loading-spinner small"></div>
                    <span>审查中...</span>
                  </>
                ) : (
                  <span>开始审查</span>
                )}
              </button>

              {reviewAlert && (
                <div className={`alert-message ${reviewAlert.type}`}>
                  {reviewAlert.message}
                </div>
              )}

              {reviewResult && (
                <div className="review-results">
                  {reviewResult.summary && (
                    <div className="result-summary">
                      <div className="result-summary-header">
                        <span>📊</span>
                        <span>审查摘要</span>
                      </div>
                      <p>{reviewResult.summary}</p>
                    </div>
                  )}
                  {reviewResult.suggestions.length > 0 ? (
                    <div className="result-suggestions">
                      <div className="result-suggestions-header">
                        <span>💡</span>
                        <span>改进建议 ({reviewResult.suggestions.length})</span>
                      </div>
                      {renderSuggestions(reviewResult.suggestions)}
                    </div>
                  ) : (
                    <div className="result-empty">
                      <p>✅ 未发现改进建议，MRT 内容质量良好！</p>
                    </div>
                  )}
                </div>
              )}
            </form>
          </section>
        )}

        {activeTab === 'chat' && (
          <section className="chat-container">
            {/* Chat Header */}
            <div className="chat-top-bar">
              <div className="chat-title-section">
                <h2 className="chat-title">智能对话审查</h2>
                <p className="chat-subtitle">上传文件或输入内容，AI 助手会帮您审查 MRT</p>
              </div>
              <button type="button" className="new-chat-btn" onClick={resetChatSession}>
                <span>🔄</span>
                <span>新对话</span>
              </button>
            </div>

            {/* Chat Messages Area */}
            <div className="chat-messages-wrapper">
              {chatHistory.length === 0 ? (
                <div className="empty-chat-state">
                  <div className="empty-chat-icon">🤖</div>
                  <h3 className="empty-chat-title">开始新的对话</h3>
                  <p className="empty-chat-desc">
                    上传 MRT 文件或输入内容，AI 助手会帮您进行审查
                  </p>
                  <div className="empty-chat-tips">
                    <div className="tip-item">
                      <span className="tip-icon">📎</span>
                      <span>支持拖拽上传文件</span>
                    </div>
                    <div className="tip-item">
                      <span className="tip-icon">💡</span>
                      <span>默认作为 MRT 文件处理</span>
                    </div>
                    <div className="tip-item">
                      <span className="tip-icon">📝</span>
                      <span>可修改和查看 checklist</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="chat-messages">
                  {chatHistory.map((turn, index) => (
                    <div key={`${turn.role}-${index}`} className={`message-wrapper ${turn.role}`}>
                      <div className="message-avatar">
                        {turn.role === 'assistant' ? '🤖' : '👤'}
                      </div>
                      <div className="message-content">
                        <div className="message-bubble">{turn.content}</div>
                      </div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="message-wrapper assistant">
                      <div className="message-avatar">🤖</div>
                      <div className="message-content">
                        <div className="message-bubble typing-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {(chatSummary || (chatSuggestions && chatSuggestions.length > 0)) && chatHistory.length > 0 && (
                <div className="chat-results">
                  {chatSummary && (
                    <div className="summary-card">
                      <div className="summary-header">
                        <span className="summary-icon">📊</span>
                        <span>审查摘要</span>
                      </div>
                      <p className="summary-text">{chatSummary}</p>
                    </div>
                  )}
                  {chatSuggestions && chatSuggestions.length > 0 && (
                    <div className="suggestions-card">
                      <div className="suggestions-header">
                        <span className="suggestions-icon">💡</span>
                        <span>改进建议 ({chatSuggestions.length})</span>
                      </div>
                      <div className="suggestions-list">
                        {chatSuggestions.map((item, idx) => (
                          <div key={`${item.checklist_id}-${idx}`} className="suggestion-item">
                            <span className="suggestion-id">{item.checklist_id}</span>
                            <span className="suggestion-text">{item.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
                        <span className="file-icon">📎</span>
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">
                          {(file.size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="file-remove-btn"
                        title="移除文件"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <form onSubmit={handleChatSubmit} className="chat-input-form">
                <div className="input-wrapper">
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                    accept=".txt,.md,.json,.text"
                    multiple
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="attach-button"
                    title="上传文件"
                    disabled={chatLoading}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                    </svg>
                  </button>
                  <textarea
                    ref={textareaRef}
                    value={chatMessage}
                    onChange={(event) => setChatMessage(event.target.value)}
                    placeholder={
                      isDragOver
                        ? '松开以上传文件...'
                        : '输入消息或拖拽文件上传...'
                    }
                    rows={1}
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
                  <button
                    type="submit"
                    disabled={chatLoading || (!chatMessage.trim() && uploadedFiles.length === 0)}
                    className="send-button"
                    title="发送 (Enter)"
                  >
                    {chatLoading ? (
                      <div className="loading-spinner"></div>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                      </svg>
                    )}
                  </button>
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
                    <div className="drag-icon">📎</div>
                    <p className="drag-text">松开以上传文件</p>
                    <p className="drag-hint">默认作为 MRT 文件处理</p>
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
