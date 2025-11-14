import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

beforeEach(() => {
  window.localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('App', () => {
  it('submits review request and renders suggestions', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          summary: '共识别到 2 条改进建议。',
          suggestions: [
            { checklist_id: 'CHK-001', message: '补充测试目标描述' },
            { checklist_id: 'CHK-002', message: '添加前置条件' },
          ],
        }),
    })
    vi.stubGlobal('fetch', mockFetch as unknown as typeof fetch)

    render(<App />)

    const mrtField = screen.getByLabelText('MRT 内容')
    fireEvent.change(mrtField, { target: { value: '示例 MRT 内容' } })

    const submitButton = screen.getByRole('button', { name: 'Review' })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('审查完成')).toBeInTheDocument()
    })

    expect(screen.getByText('共识别到 2 条改进建议。')).toBeInTheDocument()
    expect(screen.getByText('补充测试目标描述')).toBeInTheDocument()
    expect(screen.getByText('添加前置条件')).toBeInTheDocument()

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [, options] = mockFetch.mock.calls[0]
    const body = JSON.parse((options as RequestInit).body as string)
    expect(body.mrt_content).toBe('示例 MRT 内容')
  })

  it('handles chat conversation flow', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          session_id: 'abc123',
          state: 'awaiting_checklist',
          replies: ['已收到 MRT 内容。是否使用默认 Checklist？如需自定义可直接在消息中粘贴 JSON 清单。'],
          history: [
            { role: 'user', content: '这是一个测试用例，包含执行步骤和预期结果。' },
            { role: 'assistant', content: '已收到 MRT 内容。是否使用默认 Checklist？如需自定义可直接在消息中粘贴 JSON 清单。' },
          ],
        }),
    })
    vi.stubGlobal('fetch', mockFetch as unknown as typeof fetch)

    render(<App />)

    const chatTab = screen.getByRole('button', { name: '智能对话模式' })
    fireEvent.click(chatTab)

    const chatTextarea = screen.getByPlaceholderText('示例：这是我的 MRT 内容... 或 添加 checklist: [{"id":"CHK-900",...}]')
    fireEvent.change(chatTextarea, {
      target: { value: '这是一个测试用例，包含执行步骤和预期结果。' },
    })

    const sendButton = screen.getByRole('button', { name: '发送消息' })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('消息已发送')).toBeInTheDocument()
    })

    expect(screen.getByText('会话状态: awaiting_checklist')).toBeInTheDocument()
    expect(screen.getByText('Session ID: abc123')).toBeInTheDocument()
    expect(
      screen.getAllByText('已收到 MRT 内容。是否使用默认 Checklist？如需自定义可直接在消息中粘贴 JSON 清单。').length
    ).toBeGreaterThan(0)

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [, options] = mockFetch.mock.calls[0]
    const body = JSON.parse((options as RequestInit).body as string)
    expect(body.message).toBe('这是一个测试用例，包含执行步骤和预期结果。')

    expect(window.localStorage.getItem('mrt-review-chat-session')).toBeTruthy()
  })
})
