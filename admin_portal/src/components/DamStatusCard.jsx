import React from 'react'
import { Droplets, ArrowDownRight, ArrowUpRight } from 'lucide-react'

export default function DamStatusCard({ dam }) {
  const pct = dam.storage_percentage || 0
  const colorClass =
    pct < 30 ? 'text-red-600 bg-red-50 border-red-200'
    : pct < 60 ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-kisan-600 bg-kisan-50 border-kisan-200'

  const barColor =
    pct < 30 ? 'bg-red-500'
    : pct < 60 ? 'bg-amber-500'
    : 'bg-kisan-500'

  return (
    <div className={`rounded-xl border p-4 ${colorClass}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Droplets className="w-4 h-4" />
          <h3 className="text-sm font-semibold">{dam.reservoir || 'Unknown'}</h3>
        </div>
        <span className="text-lg font-bold">{pct.toFixed(1)}%</span>
      </div>

      {/* Storage bar */}
      <div className="w-full h-2 bg-white/60 rounded-full overflow-hidden mb-3">
        <div
          className={`h-full ${barColor} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1">
          <ArrowDownRight className="w-3 h-3" />
          <span>Inflow: {dam.current_inflow_cusecs ?? '—'} cusecs</span>
        </div>
        <div className="flex items-center gap-1">
          <ArrowUpRight className="w-3 h-3" />
          <span>Outflow: {dam.current_outflow_cusecs ?? '—'} cusecs</span>
        </div>
      </div>

      {dam.current_storage_mcft && (
        <p className="text-xs mt-2 opacity-75">
          Storage: {dam.current_storage_mcft} mcft / {dam.full_capacity_mcft || '—'} mcft
        </p>
      )}

      <p className="text-xs mt-1 opacity-60">
        {dam.date || 'Date unavailable'}
      </p>
    </div>
  )
}
