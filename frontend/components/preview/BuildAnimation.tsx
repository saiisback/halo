'use client'

import { useEffect, useState, useMemo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useHaloStore, type BuildStep } from '@/lib/store'
import {
  Brain,
  BookOpen,
  Code,
  Hammer,
  Rocket,
  Layout,
  Check,
  AlertCircle,
  Terminal,
  Loader2,
} from 'lucide-react'

// ─── Palette Constants ───────────────────────────────────────────────────────
// Strict gold / black / gray — no other hues.

const GOLD = 'var(--nb-gold)'
const GOLD_HEX = '#fdda24'
const GOLD_GLOW = 'rgba(253, 218, 36, 0.35)'

// ─── Build Step Metadata ─────────────────────────────────────────────────────

interface StepMeta {
  id: BuildStep
  label: string
  subtitle: string
  icon: typeof Brain
  codeSnippet: string[]
}

const STEP_META: StepMeta[] = [
  {
    id: 'analyzing',
    label: 'Analyzing',
    subtitle: 'Understanding your requirements',
    icon: Brain,
    codeSnippet: [
      '// Analyzing DApp requirements...',
      'const spec = await analyze(prompt);',
      '',
      'interface DAppSpec {',
      '  template: "token" | "nft" | "defi";',
      '  features: Feature[];',
      '  protocols: Protocol[];',
      '  security: SecurityConfig;',
      '}',
      '',
      'const plan = buildExecutionPlan(spec);',
      'console.log("Architecture ready ✓");',
    ],
  },
  {
    id: 'retrieving_docs',
    label: 'Researching',
    subtitle: 'Fetching Stellar & Soroban docs',
    icon: BookOpen,
    codeSnippet: [
      '// Retrieving Soroban SDK documentation...',
      'const docs = await rag.query({',
      '  collection: "soroban_sdk",',
      '  query: spec.requirements,',
      '  top_k: 15,',
      '});',
      '',
      '// Cross-referencing with Stellar docs',
      'const stellar_refs = await fetchStellarDocs();',
      'const context = mergeContext(docs, stellar_refs);',
      'console.log(`${context.chunks} docs loaded ✓`);',
    ],
  },
  {
    id: 'generating_rust',
    label: 'Writing Contract',
    subtitle: 'Generating Soroban smart contract',
    icon: Code,
    codeSnippet: [
      '#![no_std]',
      'use soroban_sdk::{',
      '    contract, contractimpl, contracttype,',
      '    token, Address, Env, String, Vec,',
      '};',
      '',
      '#[contract]',
      'pub struct HaloContract;',
      '',
      '#[contractimpl]',
      'impl HaloContract {',
      '    pub fn initialize(',
      '        env: Env,',
      '        admin: Address,',
      '        token: Address,',
      '    ) -> Result<(), Error> {',
      '        admin.require_auth();',
      '        // Contract initialization logic',
      '        storage::set_admin(&env, &admin);',
      '        Ok(())',
      '    }',
      '}',
    ],
  },
  {
    id: 'compiling',
    label: 'Compiling',
    subtitle: 'Building WASM artifact',
    icon: Hammer,
    codeSnippet: [
      '$ cargo build --target wasm32-unknown-unknown',
      '   Compiling soroban-sdk v20.3.0',
      '   Compiling soroban-token v20.3.0',
      '   Compiling halo-contract v0.1.0',
      '    Finished release [optimized]',
      '',
      '$ soroban contract optimize',
      '   Reading contract.wasm (148.2 KB)',
      '   Optimizing with wasm-opt -Oz',
      '   Output: contract.optimized.wasm (42.1 KB)',
      '   Size reduction: 71.6%',
      '',
      '   ✓ WASM artifact ready',
    ],
  },
  {
    id: 'deploying',
    label: 'Deploying',
    subtitle: 'Publishing to Stellar Testnet',
    icon: Rocket,
    codeSnippet: [
      '$ soroban contract deploy \\',
      '    --wasm contract.optimized.wasm \\',
      '    --network testnet',
      '',
      'Submitting transaction...',
      'Transaction hash: 7f8a...3b2c',
      'Waiting for confirmation...',
      '',
      '✓ Contract deployed successfully',
      'Contract ID: CDLZ...HALO',
      'Network: Stellar Testnet',
      'Explorer: stellar.expert/explorer/...',
    ],
  },
  {
    id: 'generating_react',
    label: 'Building UI',
    subtitle: 'Creating React frontend',
    icon: Layout,
    codeSnippet: [
      'import { useState } from "react";',
      'import { useContract } from "./hooks";',
      '',
      'export default function App() {',
      '  const { call, loading } = useContract();',
      '  const [result, setResult] = useState(null);',
      '',
      '  return (',
      '    <div className="app">',
      '      <WalletConnect />',
      '      <Dashboard contract={contract} />',
      '      <TransactionHistory />',
      '    </div>',
      '  );',
      '}',
    ],
  },
]

// ─── Typing Effect Hook ──────────────────────────────────────────────────────

function useTypingEffect(lines: string[], speed: number = 30) {
  const [displayedLines, setDisplayedLines] = useState<string[]>([])
  const [currentLine, setCurrentLine] = useState(0)
  const [currentChar, setCurrentChar] = useState(0)
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    setDisplayedLines([])
    setCurrentLine(0)
    setCurrentChar(0)
    setIsComplete(false)
  }, [lines])

  useEffect(() => {
    if (isComplete) return

    const timer = setTimeout(() => {
      if (currentLine >= lines.length) {
        setIsComplete(true)
        return
      }

      const line = lines[currentLine]
      if (currentChar < line.length) {
        setDisplayedLines((prev) => {
          const updated = [...prev]
          updated[currentLine] = line.substring(0, currentChar + 1)
          return updated
        })
        setCurrentChar((c) => c + 1)
      } else {
        setDisplayedLines((prev) => {
          const updated = [...prev]
          updated[currentLine] = line
          return updated
        })
        setCurrentLine((l) => l + 1)
        setCurrentChar(0)
      }
    }, lineIsEmpty(lines[currentLine]) ? 80 : speed + Math.random() * 20)

    return () => clearTimeout(timer)
  }, [currentLine, currentChar, lines, speed, isComplete])

  return { displayedLines, cursorLine: currentLine }
}

function lineIsEmpty(line: string | undefined): boolean {
  return !line || line.trim() === ''
}

// ─── Syntax Highlighter (gold / gray only) ───────────────────────────────────

function highlightCode(line: string): React.ReactNode[] {
  // Comments → muted gray
  if (line.trimStart().startsWith('//') || line.trimStart().startsWith('#')) {
    return [<span key={0} style={{ color: 'var(--muted)' }}>{line}</span>]
  }

  // Terminal lines → gold prompt, foreground text
  if (line.trimStart().startsWith('$') || line.trimStart().startsWith('✓')) {
    if (line.match(/^\$/)) {
      return [
        <span key={0} style={{ color: GOLD }}>{'$ '}</span>,
        <span key={1} style={{ color: 'var(--foreground)' }}>{line.slice(2)}</span>,
      ]
    }
    return [<span key={0} style={{ color: GOLD }}>{line}</span>]
  }

  // Tokenize
  const parts = line.split(
    /(\b(?:use|pub|fn|struct|impl|let|const|mut|async|await|return|import|from|export|default|function|interface|type|if|else|for|match|Ok|Err|Result)\b|"[^"]*"|'[^']*'|`[^`]*`|\/\/.*$|\b\d+\.?\d*\b|[{}();\[\],<>:=&|!+\-*/.])/g
  )

  const keywordSet = new Set([
    'use', 'pub', 'fn', 'struct', 'impl', 'let', 'const', 'mut',
    'async', 'await', 'return', 'import', 'from', 'export', 'default',
    'function', 'interface', 'type', 'if', 'else', 'for', 'match',
    'Ok', 'Err', 'Result',
  ])

  return parts.map((part, i) => {
    // Keywords → gold
    if (keywordSet.has(part)) {
      return <span key={i} style={{ color: GOLD, fontWeight: 500 }}>{part}</span>
    }
    // Strings → dim gold
    if (part.startsWith('"') || part.startsWith("'") || part.startsWith('`')) {
      return <span key={i} style={{ color: 'var(--nb-gold-dim)' }}>{part}</span>
    }
    // Numbers → foreground
    if (/^\d+\.?\d*$/.test(part)) {
      return <span key={i} style={{ color: 'var(--foreground)' }}>{part}</span>
    }
    // Punctuation → muted gray
    if (/^[{}();\[\],<>:=&|!+\-*/.]$/.test(part)) {
      return <span key={i} style={{ color: 'var(--muted)' }}>{part}</span>
    }
    // Default → foreground
    return <span key={i} style={{ color: 'var(--foreground)' }}>{part}</span>
  })
}

// ─── Particle System ─────────────────────────────────────────────────────────

function FloatingParticles({ count = 18 }: { count?: number }) {
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1,
      duration: Math.random() * 15 + 10,
      delay: Math.random() * 5,
      opacity: Math.random() * 0.3 + 0.1,
      isGold: Math.random() > 0.4, // 60% gold, 40% gray
    }))
  }, [count])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
            top: `${p.y}%`,
            backgroundColor: p.isGold ? GOLD_HEX : 'var(--muted)',
          }}
          animate={{
            y: [0, -30, 10, -20, 0],
            x: [0, 15, -10, 20, 0],
            opacity: [p.opacity, p.opacity * 2, p.opacity, p.opacity * 1.5, p.opacity],
            scale: [1, 1.5, 0.8, 1.2, 1],
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
}

// ─── Glow Orbs (gold only) ───────────────────────────────────────────────────

function GlowOrbs() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Large gold orb — top-right */}
      <motion.div
        className="absolute w-[350px] h-[350px] rounded-full blur-[120px]"
        style={{ backgroundColor: 'rgba(253, 218, 36, 0.25)', top: '5%', right: '5%' }}
        animate={{
          x: [0, -50, 20, -30, 0],
          y: [0, 30, -20, 25, 0],
          scale: [1, 1.15, 0.95, 1.1, 1],
          opacity: [0.2, 0.35, 0.15, 0.3, 0.2],
        }}
        transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* Medium gold orb — bottom-left */}
      <motion.div
        className="absolute w-[280px] h-[280px] rounded-full blur-[100px]"
        style={{ backgroundColor: 'rgba(253, 218, 36, 0.2)', bottom: '10%', left: '10%' }}
        animate={{
          x: [0, 60, -30, 40, 0],
          y: [0, -40, 20, -30, 0],
          scale: [0.9, 1.2, 0.85, 1.1, 0.9],
          opacity: [0.15, 0.3, 0.12, 0.25, 0.15],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
      />
      {/* Center gold glow */}
      <motion.div
        className="absolute w-[200px] h-[200px] rounded-full blur-[80px]"
        style={{ backgroundColor: 'rgba(253, 218, 36, 0.15)', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}
        animate={{
          scale: [1, 1.3, 0.9, 1.2, 1],
          opacity: [0.1, 0.2, 0.07, 0.15, 0.1],
        }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
      />
    </div>
  )
}

// ─── Grid Background ─────────────────────────────────────────────────────────

function GridBackground() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {/* Gold grid lines */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `
            linear-gradient(${GOLD_HEX} 1px, transparent 1px),
            linear-gradient(90deg, ${GOLD_HEX} 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />
      {/* Gold scan line */}
      <motion.div
        className="absolute left-0 right-0 h-[1px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${GOLD_HEX}, transparent)`,
          opacity: 0.15,
        }}
        animate={{ y: ['-10%', '110%'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

// ─── Code Rain (gold) ────────────────────────────────────────────────────────

function CodeRain() {
  const chars = useMemo(() => {
    const codeChars = '{}[]()<>;:=+->|&!@#$%^*~`/\\01'
    return Array.from({ length: 25 }, (_, i) => ({
      id: i,
      x: (i / 25) * 100 + Math.random() * 4 - 2,
      chars: Array.from({ length: Math.floor(Math.random() * 8) + 4 }, () =>
        codeChars[Math.floor(Math.random() * codeChars.length)]
      ),
      speed: Math.random() * 8 + 6,
      delay: Math.random() * 8,
      opacity: Math.random() * 0.08 + 0.02,
    }))
  }, [])

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none font-mono text-[10px]">
      {chars.map((col) => (
        <motion.div
          key={col.id}
          className="absolute flex flex-col gap-1"
          style={{
            left: `${col.x}%`,
            color: GOLD,
            opacity: col.opacity,
          }}
          animate={{ y: ['-20%', '120%'] }}
          transition={{
            duration: col.speed,
            delay: col.delay,
            repeat: Infinity,
            ease: 'linear',
          }}
        >
          {col.chars.map((char, i) => (
            <span key={i} style={{ opacity: 1 - i * 0.12 }}>{char}</span>
          ))}
        </motion.div>
      ))}
    </div>
  )
}

// ─── Progress Ring (gold) ────────────────────────────────────────────────────

function ProgressRing({ progress, size = 76 }: { progress: number; size?: number }) {
  const outerRadius = (size - 6) / 2
  const innerRadius = outerRadius - 6
  const outerCircumference = 2 * Math.PI * outerRadius
  const innerCircumference = 2 * Math.PI * innerRadius

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Outer gold track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={outerRadius}
          stroke={GOLD_HEX}
          strokeWidth={2}
          fill="none"
          opacity={0.12}
        />
        {/* Outer gold progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={outerRadius}
          stroke={GOLD_HEX}
          strokeWidth={2}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={outerCircumference}
          animate={{ strokeDashoffset: outerCircumference * (1 - Math.min(progress * 1.1, 1)) }}
          transition={{ duration: 1, ease: 'easeOut' }}
          opacity={0.5}
          style={{ filter: `drop-shadow(0 0 4px ${GOLD_GLOW})` }}
        />
        {/* Inner gray track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={innerRadius}
          stroke="var(--border-color)"
          strokeWidth={3}
          fill="none"
        />
        {/* Inner gold progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={innerRadius}
          stroke={GOLD_HEX}
          strokeWidth={3}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={innerCircumference}
          animate={{ strokeDashoffset: innerCircumference * (1 - progress) }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 6px ${GOLD_GLOW})` }}
        />
      </svg>
      {/* Percentage */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.span
          className="text-sm font-mono font-bold"
          style={{ color: GOLD }}
          key={Math.round(progress * 100)}
          initial={{ scale: 1.2, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {Math.round(progress * 100)}%
        </motion.span>
      </div>
    </div>
  )
}

// ─── Step Indicator (gold + gray) ────────────────────────────────────────────

function StepIndicator({ steps, currentIndex }: { steps: StepMeta[]; currentIndex: number }) {
  return (
    <div className="flex items-center gap-1">
      {steps.map((step, i) => {
        const isActive = i === currentIndex
        const isComplete = i < currentIndex
        const Icon = step.icon

        return (
          <div key={step.id} className="flex items-center">
            <motion.div
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg"
              animate={{
                backgroundColor: isActive
                  ? `${GOLD_HEX}15`
                  : isComplete
                  ? `${GOLD_HEX}08`
                  : 'transparent',
              }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className="flex items-center justify-center w-5 h-5 rounded-md"
                animate={{
                  backgroundColor: isActive ? `${GOLD_HEX}20` : 'transparent',
                  scale: isActive ? 1 : 0.85,
                }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              >
                {isComplete ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                  >
                    <Check className="w-3 h-3" style={{ color: GOLD }} />
                  </motion.div>
                ) : (
                  <Icon
                    className="w-3 h-3"
                    style={{ color: isActive ? GOLD : 'var(--muted)' }}
                  />
                )}
              </motion.div>
              {isActive && (
                <motion.span
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 'auto', opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  className="text-[10px] font-medium whitespace-nowrap overflow-hidden"
                  style={{ color: GOLD }}
                >
                  {step.label}
                </motion.span>
              )}
            </motion.div>
            {i < steps.length - 1 && (
              <motion.div
                className="w-4 h-[1px] mx-0.5"
                style={{ backgroundColor: GOLD }}
                animate={{ opacity: i < currentIndex ? 0.6 : 0.12 }}
                transition={{ duration: 0.5 }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Code Editor Window ──────────────────────────────────────────────────────

function CodeEditorWindow({ lines, stepLabel }: { lines: string[]; stepLabel: string }) {
  const { displayedLines, cursorLine } = useTypingEffect(lines, 25)
  const editorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.scrollTop = editorRef.current.scrollHeight
    }
  }, [displayedLines])

  return (
    <motion.div
      className="relative rounded-xl overflow-hidden border backdrop-blur-xl shadow-2xl"
      style={{
        borderColor: 'var(--border-color)',
        backgroundColor: 'var(--surface)',
      }}
      initial={{ y: 20, opacity: 0, scale: 0.97 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: -20, opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
    >
      {/* Gold top accent line */}
      <motion.div
        className="h-[2px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${GOLD_HEX}, transparent)`,
        }}
        animate={{ opacity: [0.4, 0.8, 0.4] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* Title Bar */}
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b"
        style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-2)' }}
      >
        <div className="flex items-center gap-2">
          {/* Gray traffic lights */}
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--muted)', opacity: 0.4 }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--muted)', opacity: 0.3 }} />
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--muted)', opacity: 0.2 }} />
          </div>
          <div className="flex items-center gap-1.5 ml-3">
            <Terminal className="w-3 h-3" style={{ color: GOLD }} />
            <span className="text-[11px] font-mono" style={{ color: GOLD }}>
              {stepLabel}
            </span>
          </div>
        </div>
        <motion.div
          className="flex items-center gap-1.5"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: GOLD_HEX }} />
          <span className="text-[10px] font-mono" style={{ color: GOLD }}>live</span>
        </motion.div>
      </div>

      {/* Code Content */}
      <div
        ref={editorRef}
        className="p-4 font-mono text-[12px] leading-[1.7] overflow-y-auto max-h-[300px] min-h-[240px]"
        style={{ scrollBehavior: 'smooth', backgroundColor: 'var(--background)' }}
      >
        {displayedLines.map((line, i) => (
          <div key={i} className="flex">
            <span
              className="inline-block w-8 text-right mr-4 select-none text-[11px]"
              style={{ color: 'var(--border-color)' }}
            >
              {i + 1}
            </span>
            <span className="flex-1">
              {highlightCode(line || '')}
              {i === cursorLine && (
                <motion.span
                  className="inline-block w-[2px] h-[14px] ml-[1px] align-middle rounded-full"
                  style={{ backgroundColor: GOLD_HEX }}
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity }}
                />
              )}
            </span>
          </div>
        ))}
        {displayedLines.length === 0 && (
          <div className="flex">
            <span
              className="inline-block w-8 text-right mr-4 select-none text-[11px]"
              style={{ color: 'var(--border-color)' }}
            >
              1
            </span>
            <motion.span
              className="inline-block w-[2px] h-[14px] rounded-full"
              style={{ backgroundColor: GOLD_HEX }}
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity }}
            />
          </div>
        )}
      </div>

      {/* Gold bottom glow line */}
      <motion.div
        className="h-[1px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${GOLD_HEX}, transparent)`,
        }}
        animate={{ opacity: [0.3, 0.7, 0.3] }}
        transition={{ duration: 2, repeat: Infinity }}
      />
    </motion.div>
  )
}

// ─── Build Log Terminal ──────────────────────────────────────────────────────

function BuildLogTerminal({ logs }: { logs: string[] }) {
  const lastLogs = logs.slice(-3)

  return (
    <motion.div
      className="rounded-lg border px-3 py-2 overflow-hidden backdrop-blur-sm"
      style={{
        borderColor: 'var(--border-color)',
        backgroundColor: 'var(--surface)',
      }}
      initial={{ y: 10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.3, duration: 0.4 }}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <div className="w-1 h-1 rounded-full" style={{ backgroundColor: GOLD_HEX }} />
        <span className="text-[9px] uppercase tracking-wider font-mono" style={{ color: GOLD, opacity: 0.6 }}>
          output
        </span>
      </div>
      <AnimatePresence mode="popLayout">
        {lastLogs.map((log, i) => (
          <motion.p
            key={log + i}
            className="text-[10px] font-mono truncate"
            style={{ color: 'var(--muted)' }}
            initial={{ y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: i === lastLogs.length - 1 ? 0.8 : 0.4 }}
            exit={{ y: -8, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <span style={{ color: GOLD }} className="mr-1.5">›</span>
            {log}
          </motion.p>
        ))}
      </AnimatePresence>
    </motion.div>
  )
}

// ─── Main Build Animation Component ──────────────────────────────────────────

export function BuildAnimation() {
  const { buildStatus, buildLogs, error } = useHaloStore()

  const currentStepIndex = STEP_META.findIndex((s) => s.id === buildStatus)
  const currentStep = STEP_META[currentStepIndex] || STEP_META[0]
  const progress = currentStepIndex >= 0 ? (currentStepIndex + 0.5) / STEP_META.length : 0

  const isError = buildStatus === 'error'

  return (
    <div
      className="relative flex h-full flex-col items-center justify-center overflow-hidden"
      style={{ backgroundColor: 'var(--background)' }}
    >
      {/* Background Layers — all gold */}
      <GridBackground />
      <CodeRain />
      <GlowOrbs />
      <FloatingParticles count={18} />

      {/* Vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 40%, var(--background) 100%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-6 w-full max-w-lg px-6">
        {/* Step Indicator */}
        <motion.div
          layout
          className="mb-2"
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          <StepIndicator steps={STEP_META} currentIndex={currentStepIndex} />
        </motion.div>

        {/* Progress Ring + Step Label */}
        <div className="flex items-center gap-5">
          <ProgressRing progress={progress} size={76} />
          <div>
            {/* Brand tag */}
            <motion.span
              className="text-[9px] uppercase tracking-[0.2em] font-semibold font-mono mb-1 block"
              style={{ color: GOLD }}
              animate={{ opacity: [0.5, 0.9, 0.5] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            >
              halo build
            </motion.span>
            <AnimatePresence mode="wait">
              <motion.h2
                key={currentStep.id}
                className="text-lg font-semibold tracking-tight"
                style={{ color: isError ? 'var(--foreground)' : GOLD }}
                initial={{ y: 10, opacity: 0, filter: 'blur(4px)' }}
                animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
                exit={{ y: -10, opacity: 0, filter: 'blur(4px)' }}
                transition={{ duration: 0.4 }}
              >
                {isError ? 'Build Failed' : currentStep.label}
              </motion.h2>
            </AnimatePresence>
            <AnimatePresence mode="wait">
              <motion.p
                key={currentStep.id + '-sub'}
                className="text-xs mt-0.5"
                style={{ color: 'var(--muted)' }}
                initial={{ y: 5, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -5, opacity: 0 }}
                transition={{ duration: 0.3, delay: 0.1 }}
              >
                {isError ? (error || 'An error occurred') : currentStep.subtitle}
              </motion.p>
            </AnimatePresence>
          </div>
        </div>

        {/* Code Editor Window */}
        {!isError && (
          <AnimatePresence mode="wait">
            <CodeEditorWindow
              key={currentStep.id}
              lines={currentStep.codeSnippet}
              stepLabel={currentStep.label}
            />
          </AnimatePresence>
        )}

        {/* Error Display */}
        {isError && error && (
          <motion.div
            className="w-full rounded-xl border backdrop-blur-xl p-4"
            style={{
              borderColor: 'var(--muted)',
              backgroundColor: 'var(--surface)',
            }}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4" style={{ color: 'var(--foreground)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>Error Details</span>
            </div>
            <p className="text-xs font-mono" style={{ color: 'var(--muted)' }}>{error}</p>
          </motion.div>
        )}

        {/* Build Logs */}
        {buildLogs.length > 0 && !isError && (
          <div className="w-full">
            <BuildLogTerminal logs={buildLogs} />
          </div>
        )}
      </div>

      {/* Bottom gradient fade */}
      <div
        className="absolute bottom-0 left-0 right-0 h-24 pointer-events-none"
        style={{ background: 'linear-gradient(to top, var(--background) 30%, transparent)' }}
      />
      <motion.div
        className="absolute bottom-0 left-0 right-0 h-[1px] pointer-events-none"
        style={{
          background: `linear-gradient(90deg, transparent, ${GOLD_HEX}, transparent)`,
        }}
        animate={{ opacity: [0.08, 0.2, 0.08] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
    </div>
  )
}
