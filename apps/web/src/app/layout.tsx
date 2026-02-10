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
            <nav className="bg-white border-b border-gray-200 px-6 py-3">
              <div className="flex items-center justify-between max-w-7xl mx-auto">
                <a href="/" className="text-xl font-bold text-gray-900">
                  PL Generator
                </a>
                <span className="text-sm text-gray-500">v0.2.0</span>
              </div>
            </nav>
            <main className="max-w-7xl mx-auto px-6 py-8">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}
