import { useState } from 'react'
import './App.css'
import { Layout } from './components/Layout'
import { ReviewPage } from './components/ReviewPage'
import { ChatPage } from './components/ChatPage'

type TabKey = 'review' | 'chat'

function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('chat')
  const [sidebarVisible, setSidebarVisible] = useState(true)

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab)
  }

  const handleSidebarToggle = () => {
    setSidebarVisible((prev) => !prev)
  }

  return (
    <Layout
      sidebarVisible={sidebarVisible}
      activeTab={activeTab}
      onSidebarToggle={handleSidebarToggle}
      onTabChange={handleTabChange}
    >
      {activeTab === 'review' && <ReviewPage />}
      {activeTab === 'chat' && <ChatPage />}
    </Layout>
  )
}

export default App
