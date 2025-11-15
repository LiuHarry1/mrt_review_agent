import { useState, useRef } from 'react'
import './App.css'
import { Layout } from './components/Layout'
import { ReviewPage } from './components/ReviewPage'
import { ChatPage } from './components/ChatPage'

type TabKey = 'review' | 'chat'

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('review')
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const resetChatRef = useRef<(() => void) | null>(null)

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab)
  }

  const handleSidebarToggle = () => {
    setSidebarVisible((prev) => !prev)
  }

  const handleNewChat = () => {
    if (resetChatRef.current) {
      resetChatRef.current()
    }
  }

  return (
    <Layout
      sidebarVisible={sidebarVisible}
      activeTab={activeTab}
      onSidebarToggle={handleSidebarToggle}
      onTabChange={handleTabChange}
      onNewChat={activeTab === 'chat' ? handleNewChat : undefined}
    >
      {activeTab === 'review' && <ReviewPage />}
      {activeTab === 'chat' && <ChatPage onResetRef={resetChatRef} />}
    </Layout>
  )
}

export default App
