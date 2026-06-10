'use client'

import { useEffect, useRef } from 'react'

interface Props {
  originLat: number
  originLon: number
  destLat: number
  destLon: number
  originName: string
  destName: string
  truckLat?: number | null
  truckLon?: number | null
}

export default function ShipmentMap({
  originLat, originLon, destLat, destLon,
  originName, destName, truckLat, truckLon,
}: Props) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return

    import('leaflet').then((L) => {
      // @ts-ignore
      delete L.Icon.Default.prototype._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      })

      const midLat = (originLat + destLat) / 2
      const midLon = (originLon + destLon) / 2

      const map = L.map(mapRef.current!, { zoomControl: true, scrollWheelZoom: false })
      mapInstanceRef.current = map

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
      }).addTo(map)

      const greenIcon = L.divIcon({
        className: '',
        html: '<div style="width:14px;height:14px;background:#22c55e;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      })
      const redIcon = L.divIcon({
        className: '',
        html: '<div style="width:14px;height:14px;background:#ef4444;border:2px solid white;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      })
      const truckIcon = L.divIcon({
        className: '',
        html: '<div style="width:12px;height:12px;background:#3b82f6;border:2px solid white;border-radius:2px;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>',
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      })

      L.marker([originLat, originLon], { icon: greenIcon })
        .addTo(map)
        .bindPopup(`<strong>Origin</strong><br/>${originName}`)

      L.marker([destLat, destLon], { icon: redIcon })
        .addTo(map)
        .bindPopup(`<strong>Destination</strong><br/>${destName}`)

      if (truckLat != null && truckLon != null) {
        L.marker([truckLat, truckLon], { icon: truckIcon })
          .addTo(map)
          .bindPopup('Truck (last GPS)')
      }

      L.polyline([[originLat, originLon], [destLat, destLon]], {
        color: '#3b82f6',
        weight: 2,
        dashArray: '6 4',
        opacity: 0.7,
      }).addTo(map)

      const points: [number, number][] = [[originLat, originLon], [destLat, destLon]]
      if (truckLat != null && truckLon != null) points.push([truckLat, truckLon])
      map.fitBounds(L.latLngBounds(points), { padding: [32, 32] })

      // Force Leaflet to recalculate container size after the DOM has settled
      setTimeout(() => map.invalidateSize(), 50)
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [originLat, originLon, destLat, destLon, truckLat, truckLon])

  return <div ref={mapRef} className="w-full h-full" />
}
