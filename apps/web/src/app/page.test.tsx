import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DashboardPage from './page'
import { api } from '@/lib/api'

vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

vi.mock('@/lib/api', () => ({
  api: {
    listProjects: vi.fn(),
    updateProject: vi.fn(),
    deleteProject: vi.fn(),
  },
}))

function renderDashboardPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  )
}

describe('DashboardPage', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows an error panel when projects loading fails', async () => {
    vi.mocked(api.listProjects).mockRejectedValueOnce(new Error('Internal Server Error'))

    renderDashboardPage()

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('プロジェクトを読み込めませんでした')).toBeInTheDocument()
    })

    expect(screen.getByText('Internal Server Error')).toBeInTheDocument()
  })
})
