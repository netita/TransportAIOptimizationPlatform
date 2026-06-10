'use client'

import { useEffect, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import type { AnomalyResult, Truck, Warehouse, Border } from '@/lib/types'

interface LiveMapProps {
  trucks: Truck[]
  warehouses: Warehouse[]
  borders: Border[]
  anomalies: AnomalyResult[]
}

function getTruckMarkerClass(truck: Truck): string {
  switch (truck.status) {
    case 'MOVING':
      return 'truck-marker-moving'
    case 'AT_BORDER':
      return 'truck-marker-border'
    case 'IDLE':
    case 'AT_WAREHOUSE':
    case 'OFFLINE':
    default:
      return 'truck-marker-idle'
  }
}

function getBorderMarkerClass(status: string): string {
  switch (status) {
    case 'CONGESTED':
      return 'border-marker-congested'
    case 'SLOW':
      return 'border-marker-slow'
    case 'CLOSED':
      return 'border-marker-closed'
    default:
      return 'border-marker-normal'
  }
}

// Main Discordia corridors — Turkey → Sofia → Germany and secondary routes
const ROUTES = [
  {
    name: 'Turkey → Sofia → Munich (Main Corridor)',
    color: '#1d4ed8',
    weight: 3,
    waypoints: [
      [41.0082, 28.9784], // Istanbul
      [41.7167, 26.3667], // Kapitan Andreevo border
      [42.6977, 23.3219], // Sofia
      [43.0500, 22.7167], // Kalotina border (BG-RS)
      [44.7866, 20.4489], // Belgrade
      [45.0500, 19.1333], // Batrovci border (RS-HR)
      [47.4979, 19.0402], // Budapest
      [47.9167, 17.0833], // Nickelsdorf border (HU-AT)
      [48.2082, 16.3738], // Vienna
      [48.1351, 11.5820], // Munich
    ],
  },
  {
    name: 'Bucharest → Berlin',
    color: '#7c3aed',
    weight: 2,
    waypoints: [
      [44.4268, 26.1025], // Bucharest
      [43.8561, 25.9697], // Ruse/Giurgiu border
      [46.1667, 21.0833], // Nadlac border (RO-HU)
      [47.4979, 19.0402], // Budapest
      [47.9167, 17.0833], // Nickelsdorf
      [48.2082, 16.3738], // Vienna
      [52.5200, 13.4050], // Berlin
    ],
  },
  {
    name: 'Sofia → Vienna',
    color: '#0891b2',
    weight: 2,
    waypoints: [
      [42.6977, 23.3219], // Sofia
      [43.8561, 25.9697], // Ruse/Giurgiu
      [44.4268, 26.1025], // Bucharest
      [46.1667, 21.0833], // Nadlac
      [47.4979, 19.0402], // Budapest
      [47.9167, 17.0833], // Nickelsdorf
      [48.2082, 16.3738], // Vienna
    ],
  },
  {
    name: 'Varna → Hamburg',
    color: '#059669',
    weight: 2,
    waypoints: [
      [43.2141, 27.9147], // Varna Port
      [43.8561, 25.9697], // Ruse/Giurgiu
      [44.4268, 26.1025], // Bucharest
      [46.1667, 21.0833], // Nadlac
      [47.4979, 19.0402], // Budapest
      [52.5200, 13.4050], // Berlin
      [53.5753, 10.0153], // Hamburg
    ],
  },
]

export default function LiveMap({ trucks, warehouses, borders, anomalies }: LiveMapProps) {
  const mapRef = useRef<any>(null)
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const truckLayerRef = useRef<any>(null)
  const warehouseLayerRef = useRef<any>(null)
  const borderLayerRef = useRef<any>(null)

  useEffect(() => {
    if (typeof window === 'undefined' || mapRef.current) return

    const L = require('leaflet')

    delete (L.Icon.Default.prototype as any)._getIconUrl
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    })

    if (!mapContainerRef.current) return

    const map = L.map(mapContainerRef.current, {
      center: [46.0, 20.0],
      zoom: 5,
      zoomControl: true,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map)

    // Draw route corridors
    ROUTES.forEach((route) => {
      L.polyline(route.waypoints, {
        color: route.color,
        weight: route.weight,
        opacity: 0.5,
        dashArray: route.name.includes('Main') ? undefined : '6, 4',
      })
        .bindTooltip(route.name, { sticky: true, className: 'text-xs' })
        .addTo(map)
    })

    mapRef.current = map
    truckLayerRef.current = L.layerGroup().addTo(map)
    warehouseLayerRef.current = L.layerGroup().addTo(map)
    borderLayerRef.current = L.layerGroup().addTo(map)

    // Fix size after container finishes rendering
    setTimeout(() => map.invalidateSize(), 100)

    const legend = L.control({ position: 'bottomleft' })
    legend.onAdd = () => {
      const div = L.DomUtil.create('div', '')
      div.style.cssText = 'background:white;border-radius:8px;box-shadow:0 1px 5px rgba(0,0,0,0.2);padding:10px;font-size:11px;line-height:1.8'
      div.innerHTML = `
        <div style="font-weight:600;color:#334155;margin-bottom:6px">Legend</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#16a34a"></span>
          <span style="color:#475569">Moving truck</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#d97706"></span>
          <span style="color:#475569">Idle truck</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#dc2626"></span>
          <span style="color:#475569">Delayed truck</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ea580c"></span>
          <span style="color:#475569">Anomaly detected</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#1d4ed8"></span>
          <span style="color:#475569">Warehouse hub</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
          <span style="display:inline-block;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:10px solid #16a34a"></span>
          <span style="color:#475569">Border crossing</span>
        </div>
        <div style="border-top:1px solid #e2e8f0;padding-top:6px;margin-top:2px">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
            <span style="display:inline-block;width:20px;height:3px;background:#1d4ed8;opacity:0.7"></span>
            <span style="color:#475569">Main corridor</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px">
            <span style="display:inline-block;width:20px;height:2px;background:#7c3aed;opacity:0.6;border-top:2px dashed #7c3aed"></span>
            <span style="color:#475569">Secondary route</span>
          </div>
        </div>
      `
      return div
    }
    legend.addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update truck markers
  useEffect(() => {
    if (!mapRef.current || !truckLayerRef.current || typeof window === 'undefined') return
    const L = require('leaflet')

    // Build a set of anomalous truck IDs for O(1) lookup
    const anomalousTruckIds = new Set(
      anomalies
        .filter((a) => a.entity_type === 'truck')
        .map((a) => a.entity_id)
    )
    // Build a map from truck_id to anomaly reason
    const anomalyReasonMap: Record<string, string> = {}
    anomalies
      .filter((a) => a.entity_type === 'truck')
      .forEach((a) => { anomalyReasonMap[a.entity_id] = a.reason })

    truckLayerRef.current.clearLayers()
    trucks.forEach((truck) => {
      const isAnomaly = anomalousTruckIds.has(truck.truck_id)
      const markerClass = isAnomaly ? 'truck-marker-anomaly' : getTruckMarkerClass(truck)
      const icon = L.divIcon({
        className: '',
        html: `<div class="${markerClass}"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      })

      const anomalyHtml = isAnomaly
        ? `<div style="color:#ea580c;font-weight:600;margin-top:4px">&#9888; ANOMALY: ${anomalyReasonMap[truck.truck_id]}</div>`
        : ''

      const popupContent = `
        <div style="min-width:160px">
          <div style="font-weight:600;color:#1d4ed8;margin-bottom:4px">${truck.truck_id}</div>
          <div style="font-size:12px;color:#475569">
            <div>Status: <strong>${truck.status}</strong></div>
            <div>Speed: <strong>${Math.round(truck.speed_kmh)} km/h</strong></div>
            ${truck.current_shipment_id ? `<div>Shipment: <strong>${truck.current_shipment_id}</strong></div>` : ''}
            <div style="color:#94a3b8;margin-top:4px">Updated: ${new Date(truck.last_updated).toLocaleTimeString()}</div>
            ${anomalyHtml}
          </div>
        </div>
      `

      L.marker([truck.lat, truck.lon], { icon })
        .bindPopup(popupContent)
        .addTo(truckLayerRef.current)
    })
  }, [trucks, anomalies])

  // Update warehouse markers
  useEffect(() => {
    if (!mapRef.current || !warehouseLayerRef.current || typeof window === 'undefined') return
    const L = require('leaflet')

    warehouseLayerRef.current.clearLayers()
    warehouses.forEach((wh) => {
      const icon = L.divIcon({
        className: '',
        html: `<div class="warehouse-marker"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      })

      const congestionPct = Math.round(wh.congestion_risk * 100)
      const popupContent = `
        <div style="min-width:180px">
          <div style="font-weight:600;color:#1d4ed8;margin-bottom:4px">${wh.name}</div>
          <div style="font-size:12px;color:#475569">
            <div>${wh.city}, ${wh.country}</div>
            <div>Congestion: <strong style="color:${congestionPct > 70 ? '#dc2626' : congestionPct > 40 ? '#d97706' : '#16a34a'}">${congestionPct}%</strong></div>
            <div>Docks: <strong>${wh.available_docks}/${wh.total_docks} free</strong></div>
            <div>Queue: <strong>${Math.round(wh.queue_time_min)} min</strong></div>
            <div>Incoming: <strong>${wh.incoming_trucks} trucks</strong></div>
          </div>
        </div>
      `

      L.marker([wh.lat, wh.lon], { icon })
        .bindPopup(popupContent)
        .addTo(warehouseLayerRef.current)
    })
  }, [warehouses])

  // Update border markers
  useEffect(() => {
    if (!mapRef.current || !borderLayerRef.current || typeof window === 'undefined') return
    const L = require('leaflet')

    borderLayerRef.current.clearLayers()
    borders.forEach((border) => {
      const markerClass = `border-marker-normal ${getBorderMarkerClass(border.status)}`
      const statusColor =
        border.status === 'NORMAL' ? '#16a34a' :
        border.status === 'SLOW' ? '#d97706' :
        border.status === 'CONGESTED' ? '#dc2626' : '#1e293b'

      const icon = L.divIcon({
        className: '',
        html: `<div style="width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-bottom:12px solid ${statusColor};filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3))"></div>`,
        iconSize: [14, 12],
        iconAnchor: [7, 12],
      })

      const popupContent = `
        <div style="min-width:180px">
          <div style="font-weight:600;color:#1d4ed8;margin-bottom:4px">${border.name}</div>
          <div style="font-size:12px;color:#475569">
            <div>Status: <strong style="color:${statusColor}">${border.status}</strong></div>
            <div>Wait time: <strong>${Math.round(border.wait_time_min)} min</strong></div>
            <div>Inspection rate: <strong>${Math.round(border.inspection_rate * 100)}%</strong></div>
            ${border.weather_risk > 0.1 ? `<div>Weather risk: <strong>${Math.round(border.weather_risk * 100)}%</strong></div>` : ''}
          </div>
        </div>
      `

      L.marker([border.lat, border.lon], { icon })
        .bindPopup(popupContent)
        .addTo(borderLayerRef.current)
    })
  }, [borders])

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-200" style={{ height: '371px' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '371px' }} />
      <div className="absolute top-3 left-3 z-[400] bg-white rounded-lg shadow-sm px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-100">
        {trucks.length} trucks &bull; {warehouses.length} hubs &bull; {borders.length} borders
      </div>
    </div>
  )
}
