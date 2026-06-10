'use client'

import { createContext, useContext, useCallback } from 'react'
import { mutate } from 'swr'
import { useWebSocket } from '@/hooks/useWebSocket'
import type { WsStatus } from '@/hooks/useWebSocket'
import type { Shipment, ShipmentListResponse } from '@/lib/types'

const WsContext = createContext<WsStatus>('connecting')

export function WsProvider({ children }: { children: React.ReactNode }) {
  const handleGpsUpdate = useCallback(() => {
    mutate('trucks')
    mutate('kpi')
    mutate('dispatcher')
    mutate('fleet')
  }, [])

  const handleShipmentUpdate = useCallback((shipmentId: string, newStatus: string) => {
    mutate(
      'shipments',
      (current: ShipmentListResponse | undefined) => {
        if (!current) return current
        return {
          ...current,
          items: current.items.map((s: Shipment) =>
            s.shipment_id === shipmentId
              ? { ...s, status: newStatus as Shipment['status'] }
              : s
          ),
        }
      },
      { revalidate: true }
    )
    mutate('kpi')
    mutate('alerts')
    mutate('dispatcher')
    mutate('fleet')
  }, [])

  const { status } = useWebSocket({
    onGpsUpdate: handleGpsUpdate,
    onShipmentUpdate: handleShipmentUpdate,
  })

  return <WsContext.Provider value={status}>{children}</WsContext.Provider>
}

export function useWsStatus(): WsStatus {
  return useContext(WsContext)
}
