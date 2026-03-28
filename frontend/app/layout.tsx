import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Drug Discovery Platform',
  description: 'End-to-end drug discovery simulation platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100`}>
        <nav className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 sticky top-0 z-50">
          <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
            <Link href="/" className="font-bold text-sm tracking-tight hover:text-blue-600 transition-colors">
              Drug Discovery Platform
            </Link>
            <div className="flex gap-4 text-sm">
              <Link href="/" className="text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">
                Pipeline
              </Link>
              <Link href="/library" className="text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors">
                History
              </Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}
