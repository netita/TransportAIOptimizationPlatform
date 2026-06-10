'use client'

import { useEffect, useRef, useState } from 'react'

export type WsStatus = 'connecting' | 'connected' | 'disconnected'

interface UseWebSocketOptions {
  onGpsUpdate?: (count: number) => void
  onShipmentUpdate?: (shipmentId: string, status: string) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const delayRef = useRef(1000)
  const mountedRef = useRef(true)

  // Keep callback refs in sync so reconnects pick up latest functions
  const onGpsUpdateRef = useRef(options.onGpsUpdate)
  const onShipmentUpdateRef = useRef(options.onShipmentUpdate)
  useEffect(() => { onGpsUpdateRef.current = options.onGpsUpdate })
  useEffect(() => { onShipmentUpdateRef.current = options.onShipmentUpdate })

  useEffect(() => {
    mountedRef.current = true

    function connect() {
      if (!mountedRef.current) return

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const wsUrl = apiUrl.replace(/^https?/, 'ws') + '/ws'

      setStatus('connecting')
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return }
        setStatus('connected')
        delayRef.current = 1000
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string)
          if (data.type === 'gps_update') {
            onGpsUpdateRef.current?.(data.count as number)
          } else if (data.type === 'shipment_update') {
            onShipmentUpdateRef.current?.(data.shipment_id as string, data.status as string)
          }
          // 'ping' and 'connected' types are silently ignored
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => ws.close()

      ws.onclose = () => {
        wsRef.current = null
        if (!mountedRef.current) return
        setStatus('disconnected')
        // exponential backoff, cap at 30 s
        const delay = Math.min(delayRef.current, 30000)
        delayRef.current = delay * 2
        timerRef.current = setTimeout(connect, delay)
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      if (timerRef.current) clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, []) // connect once on mount; callbacks go through refs

  return { status }
}
