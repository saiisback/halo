'use client'

import { useEffect, useState, useMemo } from 'react'
import {
  Search, Plus, Check, CheckCheck, Sparkles, ExternalLink, Loader2,
  BarChart3, ArrowLeftRight, Landmark, Flame, Waves,
  Satellite, Banknote, Building2, Globe, Coins, ShieldCheck, Hexagon,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useHaloStore } from '@/lib/store'

/** Map protocol IDs directly to Lucide icon components */
const PROTOCOL_ICONS: Record<string, LucideIcon> = {
  'stellar-dex': BarChart3,
  'soroswap': ArrowLeftRight,
  'blend-protocol': Landmark,
  'phoenix-protocol': Flame,
  'aquarius': Waves,
  'mercury': Satellite,
  'fxdao': Banknote,
  'sep24-anchor': Building2,
  'sep31-payments': Globe,
  'soroban-token-sac': Coins,
  'timelock-multisig': ShieldCheck,
}

function ProtocolIcon({ protocolId, className }: { protocolId: string; className?: string }) {
  const Icon = PROTOCOL_ICONS[protocolId] ?? Hexagon
  return <Icon className={className} />
}

const CATEGORY_ALL = 'All'

export function ProtocolsPanel() {
  const {
    protocols,
    suggestedProtocols,
    selectedProtocols,
    integratedProtocols,
    protocolsLoading,
    suggestionsLoading,
    buildStatus,
    isBuilding,
    loadProtocols,
    loadSuggestedProtocols,
    toggleProtocol,
  } = useHaloStore()

  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(CATEGORY_ALL)

  // Load protocols on mount
  useEffect(() => {
    loadProtocols()
  }, [loadProtocols])

  // Load AI suggestions when a DApp is built
  useEffect(() => {
    if (buildStatus === 'complete') {
      loadSuggestedProtocols()
    }
  }, [buildStatus, loadSuggestedProtocols])

  // Derive categories from loaded protocols
  const categories = useMemo(() => {
    const cats = Array.from(new Set(protocols.map(p => p.category)))
    return [CATEGORY_ALL, ...cats.sort()]
  }, [protocols])

  // Filter protocols
  const filteredProtocols = useMemo(() => {
    return protocols.filter(p => {
      const matchesSearch =
        !search ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.description.toLowerCase().includes(search.toLowerCase())
      const matchesCategory =
        selectedCategory === CATEGORY_ALL || p.category === selectedCategory
      return matchesSearch && matchesCategory
    })
  }, [protocols, search, selectedCategory])

  const hasDApp = buildStatus === 'complete'

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-3 border-b border-[var(--border-color)]">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--muted)]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search protocols..."
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg
                       bg-[var(--surface)] border border-[var(--border-color)]
                       text-[var(--foreground)] placeholder:text-[var(--muted)]
                       focus:outline-none focus:border-[var(--nb-gold)]/50
                       transition-colors"
          />
        </div>
      </div>

      {/* Category chips */}
      <div className="flex gap-1.5 px-3 py-2 overflow-x-auto border-b border-[var(--border-color)] scrollbar-none">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`shrink-0 px-2.5 py-1 text-[10px] font-medium rounded-full transition-all
              ${
                selectedCategory === cat
                  ? 'bg-[var(--nb-gold)] text-black'
                  : 'bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--foreground)]'
              }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* AI Suggestions section */}
        {hasDApp && (suggestedProtocols.length > 0 || suggestionsLoading) && (
          <div className="px-3 pt-3 pb-1">
            <div className="flex items-center gap-1.5 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-[var(--nb-gold)]" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--nb-gold)]">
                AI Recommended
              </span>
            </div>
            {suggestionsLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--muted)]" />
                <span className="ml-2 text-xs text-[var(--muted)]">Analyzing your DApp...</span>
              </div>
            ) : (
              <div className="space-y-2 mb-3">
                {suggestedProtocols.map(sp => (
                  <SuggestedCard
                    key={sp.id}
                    protocolId={sp.id}
                    name={sp.name}
                    reason={sp.reason}
                    category={sp.category}
                    isSelected={selectedProtocols.includes(sp.id)}
                    isIntegrated={integratedProtocols.includes(sp.id)}
                    isBuilding={isBuilding}
                    onToggle={() => {
                      const full = protocols.find(p => p.id === sp.id)
                      toggleProtocol(full ?? sp)
                    }}
                  />
                ))}
              </div>
            )}
            <div className="border-b border-[var(--border-color)]" />
          </div>
        )}

        {/* Protocol list */}
        {protocolsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-[var(--muted)]" />
          </div>
        ) : filteredProtocols.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <p className="text-xs text-[var(--muted)]">No protocols found</p>
            {search && (
              <button
                onClick={() => setSearch('')}
                className="mt-2 text-[10px] text-[var(--nb-gold)] hover:underline"
              >
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="p-3 space-y-2">
            {filteredProtocols.map(protocol => (
              <ProtocolCard
                key={protocol.id}
                protocolId={protocol.id}
                name={protocol.name}
                description={protocol.description}
                category={protocol.category}
                docsUrl={protocol.docs_url}
                isSelected={selectedProtocols.includes(protocol.id)}
                isIntegrated={integratedProtocols.includes(protocol.id)}
                isBuilding={isBuilding}
                onToggle={() => toggleProtocol(protocol)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProtocolCard({
  protocolId,
  name,
  description,
  category,
  docsUrl,
  isSelected,
  isIntegrated,
  isBuilding,
  onToggle,
}: {
  protocolId: string
  name: string
  description: string
  category: string
  docsUrl?: string | null
  isSelected: boolean
  isIntegrated: boolean
  isBuilding: boolean
  onToggle: () => void
}) {
  return (
    <div
      className={`group rounded-lg border p-3 transition-all cursor-pointer
        ${
          isSelected
            ? 'border-[var(--nb-gold)]/40 bg-[var(--nb-gold)]/[0.06]'
            : isIntegrated
              ? 'border-[var(--nb-green)]/30 bg-[var(--nb-green)]/[0.04]'
              : 'border-[var(--border-color)] bg-[var(--surface)]/50 hover:border-[var(--nb-gold)]/30 hover:bg-[var(--surface)]'
        }`}
      onClick={() => !isIntegrated && !isBuilding && onToggle()}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`flex items-center justify-center w-8 h-8 rounded-lg shrink-0 transition-colors
            ${isSelected ? 'bg-[var(--nb-gold)]/15 text-[var(--nb-gold)]'
              : isIntegrated ? 'bg-[var(--nb-green)]/15 text-[var(--nb-green)]'
              : 'bg-[var(--surface-2)] text-[var(--muted)] group-hover:text-[var(--nb-gold)] group-hover:bg-[var(--nb-gold)]/10'}`}>
            <ProtocolIcon protocolId={protocolId} className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="text-xs font-semibold text-[var(--foreground)] truncate">{name}</h3>
              {docsUrl && (
                <a
                  href={docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  title="View docs"
                >
                  <ExternalLink className="w-3 h-3 text-[var(--muted)] hover:text-[var(--nb-gold)]" />
                </a>
              )}
            </div>
            <span className="text-[10px] text-[var(--muted)]">{category}</span>
          </div>
        </div>

        <span
          className={`shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium transition-all
            ${
              isIntegrated
                ? 'bg-[var(--nb-green)]/15 text-[var(--nb-green)]'
                : isSelected
                  ? 'bg-[var(--nb-gold)]/20 text-[var(--nb-gold)]'
                  : isBuilding
                    ? 'bg-[var(--surface-2)] text-[var(--muted)]'
                    : 'bg-[var(--nb-gold)]/10 text-[var(--nb-gold)] group-hover:bg-[var(--nb-gold)]/20'
            }`}
        >
          {isIntegrated ? (
            <>
              <CheckCheck className="w-3 h-3" />
              Integrated
            </>
          ) : isSelected ? (
            <>
              <Check className="w-3 h-3" />
              Selected
            </>
          ) : (
            <>
              <Plus className="w-3 h-3" />
              Add
            </>
          )}
        </span>
      </div>

      {/* Description */}
      <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--muted)] line-clamp-2">
        {description}
      </p>
    </div>
  )
}

function SuggestedCard({
  protocolId,
  name,
  reason,
  category,
  isSelected,
  isIntegrated,
  isBuilding,
  onToggle,
}: {
  protocolId: string
  name: string
  reason: string
  category: string
  isSelected: boolean
  isIntegrated: boolean
  isBuilding: boolean
  onToggle: () => void
}) {
  return (
    <div
      className={`rounded-lg border p-2.5 transition-all cursor-pointer
        ${
          isSelected
            ? 'border-[var(--nb-gold)]/40 bg-[var(--nb-gold)]/[0.08]'
            : isIntegrated
              ? 'border-[var(--nb-green)]/30 bg-[var(--nb-green)]/[0.04]'
              : 'border-[var(--nb-gold)]/20 bg-[var(--nb-gold)]/[0.03] hover:border-[var(--nb-gold)]/40'
        }`}
      onClick={() => !isIntegrated && !isBuilding && onToggle()}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={`flex items-center justify-center w-7 h-7 rounded-md shrink-0
            ${isSelected ? 'bg-[var(--nb-gold)]/15 text-[var(--nb-gold)]'
              : isIntegrated ? 'bg-[var(--nb-green)]/15 text-[var(--nb-green)]'
              : 'bg-[var(--nb-gold)]/10 text-[var(--nb-gold)]'}`}>
            <ProtocolIcon protocolId={protocolId} className="w-3.5 h-3.5" />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-[var(--foreground)]">{name}</h4>
            <span className="text-[10px] text-[var(--muted)]">{category}</span>
          </div>
        </div>
        <span
          className={`shrink-0 flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium transition-all
            ${
              isIntegrated
                ? 'bg-[var(--nb-green)]/15 text-[var(--nb-green)]'
                : isSelected
                  ? 'bg-[var(--nb-gold)]/20 text-[var(--nb-gold)]'
                  : 'bg-[var(--nb-gold)]/10 text-[var(--nb-gold)]'
            }`}
        >
          {isIntegrated ? (
            <>
              <CheckCheck className="w-3 h-3" />
              Integrated
            </>
          ) : isSelected ? (
            <>
              <Check className="w-3 h-3" />
              Selected
            </>
          ) : (
            <>
              <Plus className="w-3 h-3" />
              Add
            </>
          )}
        </span>
      </div>
      <p className="mt-1 text-[10px] leading-relaxed text-[var(--muted)] italic">{reason}</p>
    </div>
  )
}
