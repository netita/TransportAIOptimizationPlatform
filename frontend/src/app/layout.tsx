import type { Metadata } from 'next'
import './globals.css'
import { WsProvider } from '@/context/WsContext'

export const metadata: Metadata = {
  title: 'Discordia AI Operations Platform',
  description: 'AI-augmented logistics operations platform for Discordia Transport — Bulgaria\'s largest transport company. 1500+ trucks, 70 countries.',
  keywords: ['logistics', 'transport', 'AI', 'operations', 'Discordia'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        <WsProvider>{children}</WsProvider>
      </body>
    </html>
  )
}
