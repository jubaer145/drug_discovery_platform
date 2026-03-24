import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
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
        {children}
      </body>
    </html>
  )
}
