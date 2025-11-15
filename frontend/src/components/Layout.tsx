import React, { useEffect } from 'react'

interface LayoutProps {
  sidebarVisible: boolean
  activeTab: 'review' | 'chat'
  onSidebarToggle: () => void
  onTabChange: (tab: 'review' | 'chat') => void
  onNewChat?: () => void
  children: React.ReactNode
}

export function Layout({
  sidebarVisible,
  activeTab,
  onSidebarToggle,
  onTabChange,
  onNewChat,
  children,
}: LayoutProps) {
  // Update body class based on sidebar visibility
  useEffect(() => {
    if (sidebarVisible) {
      document.body.classList.add('sidebar-visible')
      document.body.classList.remove('sidebar-hidden')
    } else {
      document.body.classList.add('sidebar-hidden')
      document.body.classList.remove('sidebar-visible')
    }
  }, [sidebarVisible])

  return (
    <div className="app">
      {/* Top Bar */}
      <header className={`top-bar ${sidebarVisible ? 'with-sidebar' : 'no-sidebar'}`}>
        <div className="top-bar-left">
          {!sidebarVisible && (
            <button
              type="button"
              className="sidebar-toggle-top"
              onClick={onSidebarToggle}
              title="Show menu"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          )}
          {activeTab === 'chat' && onNewChat && (
            <button type="button" className="new-chat-btn-top" onClick={onNewChat}>
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
            onClick={onSidebarToggle}
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
            onClick={() => onTabChange('chat')}
          >
            <span className="nav-text">Chat Review</span>
          </button>
          <button
            type="button"
            className={`nav-item ${activeTab === 'review' ? 'active' : ''}`}
            onClick={() => onTabChange('review')}
          >
            <span className="nav-text">Quick Review</span>
          </button>
        </nav>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${sidebarVisible ? 'with-sidebar' : 'no-sidebar'}`}>
        {children}
      </main>
    </div>
  )
}

