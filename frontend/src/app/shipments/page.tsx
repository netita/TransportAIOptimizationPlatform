'use client'

import { useState } from 'react'
import useSWR from 'swr'
import Header from '@/components/Header'
import ShipmentsTable from '@/components/ShipmentsTable'
import { getShipments } from '@/lib/api'
import type { ShipmentStatus, Priority } from '@/lib/types'
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'IN_TRANSIT', label: 'In Transit' },
  { value: 'DELAYED', label: 'Delayed' },
  { value: 'AT_BORDER', label: 'At Border' },
  { value: 'AT_WAREHOUSE', label: 'At Warehouse' },
  { value: 'DELIVERED', label: 'Delivered' },
  { value: 'PENDING', label: 'Pending' },
]

const PRIORITY_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Priorities' },
  { value: 'CRITICAL', label: 'Critical' },
  { value: 'HIGH', label: 'High' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
]

const PAGE_SIZE = 20

const statusCounts: Record<string, string> = {
  IN_TRANSIT: 'bg-blue-100 text-blue-800',
  DELAYED: 'bg-red-100 text-red-800',
  AT_BORDER: 'bg-amber-100 text-amber-800',
  AT_WAREHOUSE: 'bg-purple-100 text-purple-800',
  DELIVERED: 'bg-green-100 text-green-800',
  PENDING: 'bg-slate-100 text-slate-600',
}

export default function ShipmentsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [carrierSearch, setCarrierSearch] = useState('')
  const [page, setPage] = useState(0)

  const fetcher = () =>
    getShipments({
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
      carrier: carrierSearch || undefined,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    })

  const { data, isLoading } = useSWR(
    ['shipments-page', statusFilter, priorityFilter, carrierSearch, page],
    fetcher,
    { refreshInterval: 15000 }
  )

  const { data: allData } = useSWR(
    ['shipments-all'],
    () => getShipments({ limit: 500 }),
    { refreshInterval: 15000 }
  )

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  const statusSummary = allData
    ? STATUS_OPTIONS.slice(1).map((opt) => ({
        label: opt.label,
        value: opt.value,
        count: allData.items.filter((s) => s.status === opt.value).length,
      }))
    : []

  function handleFilterChange() {
    setPage(0)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Page title */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Shipments</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage and monitor all active shipments across the Discordia network.
          </p>
        </div>

        {/* Status summary bar */}
        {statusSummary.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {statusSummary.map((s) => (
              <button
                key={s.value}
                onClick={() => {
                  setStatusFilter(s.value === statusFilter ? '' : s.value)
                  handleFilterChange()
                }}
                className={clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
                  s.value === statusFilter
                    ? `${statusCounts[s.value]} border-current shadow-sm`
                    : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                )}
              >
                <span>{s.label}</span>
                <span
                  className={clsx(
                    'px-1.5 py-0.5 rounded-md text-xs font-bold',
                    s.value === statusFilter ? 'bg-white/50' : 'bg-slate-100 text-slate-600'
                  )}
                >
                  {s.count}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Filter bar */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 px-5 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
              <Filter className="w-4 h-4" />
              Filters
            </div>

            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                handleFilterChange()
              }}
              className="px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => {
                setPriorityFilter(e.target.value)
                handleFilterChange()
              }}
              className="px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
            >
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={carrierSearch}
                onChange={(e) => {
                  setCarrierSearch(e.target.value)
                  handleFilterChange()
                }}
                placeholder="Search carrier..."
                className="text-sm bg-transparent outline-none w-36 text-slate-700 placeholder-slate-400"
              />
            </div>

            {(statusFilter || priorityFilter || carrierSearch) && (
              <button
                onClick={() => {
                  setStatusFilter('')
                  setPriorityFilter('')
                  setCarrierSearch('')
                  setPage(0)
                }}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                Clear filters
              </button>
            )}

            <div className="ml-auto text-sm text-slate-500">
              {data ? (
                <>
                  Showing {page * PAGE_SIZE + 1}–
                  {Math.min((page + 1) * PAGE_SIZE, data.total)} of{' '}
                  <strong className="text-slate-700">{data.total}</strong> shipments
                </>
              ) : (
                'Loading...'
              )}
            </div>
          </div>
        </div>

        {/* Table */}
        <ShipmentsTable
          shipments={data?.items || []}
          isLoading={isLoading}
          showAll={true}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className={clsx(
                'flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors',
                page === 0
                  ? 'text-slate-300 border-slate-100 cursor-not-allowed'
                  : 'text-slate-600 border-slate-200 hover:bg-slate-50'
              )}
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <div className="flex items-center gap-1">
              {[...Array(Math.min(totalPages, 7))].map((_, i) => {
                const pageNum = i
                return (
                  <button
                    key={i}
                    onClick={() => setPage(pageNum)}
                    className={clsx(
                      'w-9 h-9 rounded-lg text-sm font-medium transition-colors',
                      pageNum === page
                        ? 'bg-blue-700 text-white'
                        : 'text-slate-600 hover:bg-slate-100'
                    )}
                  >
                    {pageNum + 1}
                  </button>
                )
              })}
            </div>

            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className={clsx(
                'flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium border transition-colors',
                page >= totalPages - 1
                  ? 'text-slate-300 border-slate-100 cursor-not-allowed'
                  : 'text-slate-600 border-slate-200 hover:bg-slate-50'
              )}
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
