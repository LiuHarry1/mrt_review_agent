import { useEffect, useRef, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat } from '../hooks/useChat'
import { useFileUpload } from '../hooks/useFileUpload'
import { uploadFile } from '../api'
import { Alert } from './Alert'
import { FileUploadArea } from './FileUploadArea'
import { MessageList } from './MessageList'

interface FileWithContent {
  file: File
  content?: string
  loading?: boolean
  error?: string
  progress?: number
}

export function ChatPage() {
  const {
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
  } = useChat()

  const {
    uploadedFiles,
    dragOver,
    fileInputRef,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileSelect,
    removeFile,
    clearFiles,
    openFileDialog,
    formatErrorMessages,
  } = useFileUpload()

  const [filesWithContent, setFilesWithContent] = useState<FileWithContent[]>([])

  // Upload files to backend immediately when they're added
  useEffect(() => {
    const uploadFiles = async () => {
      const newFiles = uploadedFiles.filter(
        (file) => !filesWithContent.find((fwc) => fwc.file === file)
      )

      if (newFiles.length === 0) return

      // Immediately add new files with loading state
      setFilesWithContent((prev) => {
        const newFilesWithContent = newFiles.map((file) => ({ 
          file, 
          loading: true, 
          progress: 0 
        }))
        return [...prev, ...newFilesWithContent]
      })

      // Upload each new file immediately
      for (const file of newFiles) {
        try {
          const result = await uploadFile(
            file,
            (progress) => {
              // Update progress in real-time
              setFilesWithContent((prev) =>
                prev.map((fwc) =>
                  fwc.file === file ? { ...fwc, progress } : fwc
                )
              )
            }
          )
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, content: result.content, loading: false, progress: 100 } 
                : fwc
            )
          )
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Upload failed'
          setFilesWithContent((prev) =>
            prev.map((fwc) =>
              fwc.file === file 
                ? { file, loading: false, error: errorMessage, progress: 0 } 
                : fwc
            )
          )
          setAlert({ type: 'error', message: `Failed to upload ${file.name}: ${errorMessage}` })
        }
      }
    }

    uploadFiles()
    // Remove filesWithContent from dependencies to avoid circular updates
    // We only want to trigger when uploadedFiles changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadedFiles, setAlert])

  // Sync with uploadedFiles (remove if removed from uploadedFiles)
  useEffect(() => {
    setFilesWithContent((prev) => prev.filter((fwc) => uploadedFiles.includes(fwc.file)))
  }, [uploadedFiles])

  const handleRemoveFile = (index: number) => {
    removeFile(index)
  }

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesWrapperRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

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
  }, [message])

  // When starting a new empty chat, scroll to top and focus textarea
  useEffect(() => {
    if (!loading && history.length === 0) {
      if (messagesWrapperRef.current) {
        messagesWrapperRef.current.scrollTop = 0
      }
      if (textareaRef.current) {
        textareaRef.current.focus()
      }
    }
  }, [history.length, loading])

  // During streaming or when new messages arrive, keep scroll at bottom
  // only when user is already near the bottom (autoScroll = true)
  useEffect(() => {
    if (autoScroll && messagesWrapperRef.current) {
      messagesWrapperRef.current.scrollTop = messagesWrapperRef.current.scrollHeight
    }
  }, [history, loading, autoScroll])

  const handleMessagesScroll = () => {
    const container = messagesWrapperRef.current
    if (!container) return
    const threshold = 40 // px
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    setAutoScroll(distanceToBottom <= threshold)
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    // Handle file upload if files are present
    const readyFiles = filesWithContent.filter((fwc) => fwc.content && !fwc.loading && !fwc.error)
    
    if (readyFiles.length > 0) {
      try {
        // Send message with file contents (filename and content)
        const filesData = readyFiles.map((fwc) => ({
          name: fwc.file.name,
          content: fwc.content!,
        }))

        // Clear input and files immediately before sending
        setMessage('')
        clearFiles()
        setFilesWithContent([])

        // Send message (don't await, let it stream in background)
        sendMessage(message.trim() || undefined, filesData).catch((error) => {
          const errorMessage = error instanceof Error ? error.message : 'Send failed'
          setAlert({ type: 'error', message: errorMessage })
        })
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Send failed'
        setAlert({ type: 'error', message: errorMessage })
      }
      return
    }

    // Check if there are files still loading
    if (filesWithContent.some((fwc) => fwc.loading)) {
      setAlert({ type: 'error', message: 'Please wait for files to finish uploading' })
      return
    }

    // Check if there are files with errors
    const errorFiles = filesWithContent.filter((fwc) => fwc.error)
    if (errorFiles.length > 0) {
      setAlert({ type: 'error', message: 'Some files failed to upload. Please remove them and try again.' })
      return
    }

    // Handle text message only
    if (message.trim()) {
      // Clear input immediately before sending
      const messageToSend = message.trim()
      setMessage('')
      
      // Send message (don't await, let it stream in background)
      sendMessage(messageToSend).catch((error) => {
        const errorMessage = error instanceof Error ? error.message : 'Send failed'
        setAlert({ type: 'error', message: errorMessage })
      })
    }
  }

  const handleDropWithValidation = (e: React.DragEvent<HTMLDivElement>) => {
    const errors = handleDrop(e)
    if (errors.length > 0) {
      const errorMessage = formatErrorMessages(errors)
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  return (
    <section className="chat-container">
      {/* Chat Messages Area */}
      <div
        className="chat-messages-wrapper"
        ref={messagesWrapperRef}
        onScroll={handleMessagesScroll}
      >
        <MessageList history={history} loading={loading} messagesEndRef={messagesEndRef} />

        {(summary || (suggestions && suggestions.length > 0)) && history.length > 0 && (
          <div className="chat-results">
            <div className="result-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {`${summary ? `## Review Summary\n\n${summary}\n\n` : ''}${
                  suggestions && suggestions.length > 0
                    ? `## Improvement Suggestions (${suggestions.length})\n\n${suggestions
                        .map((item) => `- **${item.checklist_id}**: ${item.message}`)
                        .join('\n')}\n`
                    : ''
                }`}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {/* Chat Input Area */}
      <div className="chat-input-container-wrapper">
        {/* Input area */}
        <FileUploadArea
          uploadedFiles={[]}
          dragOver={dragOver}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDropWithValidation}
          onFileSelect={handleFileSelect}
          onRemoveFile={removeFile}
          fileInputRef={fileInputRef}
        >
          <form onSubmit={handleSubmit} className="chat-input-form">
            <div className="chat-input-wrapper">
              {/* File preview inside input box (ChatGPT style) */}
              {filesWithContent.length > 0 && (
                <div className="files-preview-inside">
                  {filesWithContent.map((fwc, index) => (
                    <div key={index} className={`file-preview-chip ${fwc.error ? 'error' : ''} ${fwc.loading ? 'loading' : ''}`}>
                      <div className="file-chip-icon">
                        {fwc.loading ? (
                          <div className="loading-spinner small"></div>
                        ) : fwc.error ? (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="8" x2="12" y2="12" />
                            <line x1="12" y1="16" x2="12.01" y2="16" />
                          </svg>
                        ) : (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                            <polyline points="10 9 9 9 8 9" />
                          </svg>
                        )}
                      </div>
                      <span className="file-chip-name">{fwc.file.name}</span>
                      {fwc.error && <span className="file-chip-error">✗</span>}
                      {fwc.loading && fwc.progress !== undefined && (
                        <div className="file-chip-progress">
                          <div className="file-chip-progress-bar">
                            <div 
                              className="file-chip-progress-fill" 
                              style={{ width: `${fwc.progress}%` }}
                            ></div>
                          </div>
                          <span className="file-chip-progress-text">{fwc.progress}%</span>
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(uploadedFiles.indexOf(fwc.file))}
                        className="file-chip-remove"
                        title="Remove file"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={
                  dragOver
                    ? 'Release to upload file...'
                    : 'Enter message or drag and drop file to upload...'
                }
                rows={3}
                className="chat-textarea"
                disabled={loading}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                  if (!loading && (message.trim() || filesWithContent.filter(fwc => fwc.content && !fwc.error).length > 0)) {
                    handleSubmit(e as any)
                  }
                  }
                }}
              />
              <div className="chat-input-actions">
                <button
                  type="button"
                  onClick={openFileDialog}
                  className="attach-button"
                  title="Upload file"
                  disabled={loading}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>
                <button
                  type="submit"
                  disabled={loading || (!message.trim() && filesWithContent.filter(fwc => fwc.content && !fwc.error).length === 0)}
                  className="send-button"
                  title="Send (Enter)"
                >
                  {loading ? (
                    <div className="loading-spinner"></div>
                  ) : (
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M12 19V5M5 12l7-7 7 7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            {alert && <Alert type={alert.type} message={alert.message} className="alert-toast" />}
          </form>
        </FileUploadArea>
      </div>
    </section>
  )
}

