import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'PL Generator',
    template: '%s | PL Generator',
  },
  description: '収益計画を楽しく作る — AI-powered financial model generator',
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://pl-generator.vercel.app'),
  openGraph: {
    title: 'PL Generator',
    description: '事業計画書からAIが収益モデルを自動生成',
    siteName: 'PL Generator',
    locale: 'ja_JP',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'PL Generator',
    description: '事業計画書からAIが収益モデルを自動生成',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-gray-50">
            <nav className="bg-white border-b border-gray-200 px-4 sm:px-6 py-3">
              <div className="flex items-center justify-between max-w-7xl mx-auto">
                <a href="/" className="text-lg sm:text-xl font-bold text-gray-900 min-h-[44px] flex items-center">
                  PL Generator
                </a>
                <div className="flex items-center gap-3 sm:gap-4">
                  <a
                    href="/admin/llm-config"
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-purple-600 transition-colors min-h-[44px] min-w-[44px] justify-center"
                    title="LLM設定管理"
                  >
                    <svg className="w-4 h-4 sm:w-3.5 sm:h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span className="hidden sm:inline">管理者</span>
                  </a>
                  <span className="text-xs sm:text-sm text-gray-500">v0.2.0</span>
                </div>
              </div>
            </nav>
            <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
