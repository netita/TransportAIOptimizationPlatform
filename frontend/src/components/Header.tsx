'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Truck } from 'lucide-react'
import clsx from 'clsx'
import { useWsStatus } from '@/context/WsContext'

export default function Header() {
  const wsStatus = useWsStatus()
  const [currentTime, setCurrentTime] = useState<string>('')
  const pathname = usePathname()

  useEffect(() => {
    const update = () => {
      setCurrentTime(
        new Date().toLocaleTimeString('en-GB', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          timeZone: 'Europe/Sofia',
        }) + ' EET'
      )
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  const navLinks = [
    { href: '/', label: 'Dashboard' },
    { href: '/shipments', label: 'Shipments' },
    { href: '/analytics', label: 'Analytics' },
  ]

  return (
    <header className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-700">
              <Truck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-lg font-bold text-blue-700 tracking-wide leading-none">
                DISCORDIA
              </div>
              <div className="text-xs text-slate-500 leading-none mt-0.5">
                AI Operations Platform
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  pathname === link.href
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right side: WS status indicator + time */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {wsStatus === 'connected' && (
                <>
                  <div className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
                  </div>
                  <span className="text-xs font-semibold text-green-600 uppercase tracking-wider">Live</span>
                </>
              )}
              {wsStatus === 'connecting' && (
                <>
                  <div className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-yellow-500" />
                  </div>
                  <span className="text-xs font-semibold text-yellow-600 uppercase tracking-wider">Connecting</span>
                </>
              )}
              {wsStatus === 'disconnected' && (
                <>
                  <div className="relative flex h-2.5 w-2.5">
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
                  </div>
                  <span className="text-xs font-semibold text-red-500 uppercase tracking-wider">Reconnecting</span>
                </>
              )}
            </div>
            <div className="hidden sm:block text-sm font-mono text-slate-500 tabular-nums">
              {currentTime}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
