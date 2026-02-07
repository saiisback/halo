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
} from 'lucide-react'

// ─── Build Step Metadata ─────────────────────────────────────────────────────

interface StepMeta {
  id: BuildStep
  label: string
  subtitle: string
  icon: typeof Brain
  color: string
  glow: string
  codeSnippet: string[]
}

const STEP_META: StepMeta[] = [
  {
    id: 'analyzing',
    label: 'Analyzing',
    subtitle: 'Understanding your requirements',
    icon: Brain,
    color: '#6e56cf',
    glow: 'rgba(110, 86, 207, 0.4)',
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
    color: '#3e63dd',
    glow: 'rgba(62, 99, 221, 0.4)',
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
    color: '#05a2c2',
    glow: 'rgba(5, 162, 194, 0.4)',
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
    color: '#ffb224',
    glow: 'rgba(255, 178, 36, 0.4)',
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
    color: '#fdda24',
    glow: 'rgba(253, 218, 36, 0.4)',
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
    color: '#30a46c',
    glow: 'rgba(48, 164, 108, 0.4)',
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
        // Move to next line
        setDisplayedLines((prev) => {
          const updated = [...prev]
          updated[currentLine] = line
          return updated
        })
        setCurrentLine((l) => l + 1)
        setCurrentChar(0)
      }
    }, line_is_empty(lines[currentLine]) ? 80 : speed + Math.random() * 20)

    return () => clearTimeout(timer)
  }, [currentLine, currentChar, lines, speed, isComplete])

  return { displayedLines, isComplete, cursorLine: currentLine, cursorChar: currentChar }
}

function line_is_empty(line: string | undefined): boolean {
  return !line || line.trim() === ''
}

// ─── Syntax Highlighter ──────────────────────────────────────────────────────

function highlightCode(line: string, stepColor: string): React.ReactNode[] {
  const tokens: React.ReactNode[] = []
  // Simple keyword-based highlighting
  const keywords = /\b(use|pub|fn|struct|impl|let|const|mut|async|await|return|import|from|export|default|function|interface|type|if|else|for|match|Ok|Err|Result|Self|self|env|true|false)\b/g
  const strings = /(["'`])(?:(?!\1).)*\1/g
  const comments = /(\/\/.*$|\/\*[\s\S]*?\*\/|#!\[.*?\]|#\[.*?\])/gm
  const numbers = /\b\d+\.?\d*\b/g
  const symbols = /(\$\s*)/g

  let remaining = line
  let key = 0

  // Comment lines
  if (remaining.trimStart().startsWith('//') || remaining.trimStart().startsWith('#')) {
    return [<span key={0} style={{ color: '#6a737d' }}>{remaining}</span>]
  }

  // Terminal lines
  if (remaining.trimStart().startsWith('$') || remaining.trimStart().startsWith('✓')) {
    const dollarMatch = remaining.match(/^\$/)
    if (dollarMatch) {
      return [
        <span key={0} style={{ color: stepColor }}>{'$ '}</span>,
        <span key={1} style={{ color: '#e8e8e8' }}>{remaining.slice(2)}</span>,
      ]
    }
    return [<span key={0} style={{ color: stepColor }}>{remaining}</span>]
  }

  // Simple pass - color keywords
  const parts = remaining.split(/(\b(?:use|pub|fn|struct|impl|let|const|mut|async|await|return|import|from|export|default|function|interface|type|if|else|for|match|Ok|Err|Result)\b|"[^"]*"|'[^']*'|`[^`]*`|\/\/.*$|\b\d+\.?\d*\b|[{}();\[\],<>:=&|!+\-*/.])/g)

  const keywordSet = new Set(['use', 'pub', 'fn', 'struct', 'impl', 'let', 'const', 'mut', 'async', 'await', 'return', 'import', 'from', 'export', 'default', 'function', 'interface', 'type', 'if', 'else', 'for', 'match', 'Ok', 'Err', 'Result'])

  return parts.map((part, i) => {
    if (keywordSet.has(part)) {
      return <span key={i} style={{ color: '#c678dd', fontWeight: 500 }}>{part}</span>
    }
    if (part.startsWith('"') || part.startsWith("'") || part.startsWith('`')) {
      return <span key={i} style={{ color: '#98c379' }}>{part}</span>
    }
    if (/^\d+\.?\d*$/.test(part)) {
      return <span key={i} style={{ color: '#d19a66' }}>{part}</span>
    }
    if (/^[{}();\[\],<>:=&|!+\-*/.]$/.test(part)) {
      return <span key={i} style={{ color: '#abb2bf' }}>{part}</span>
    }
    return <span key={i} style={{ color: '#e8e8e8' }}>{part}</span>
  })
}

// ─── Particle System ─────────────────────────────────────────────────────────

function FloatingParticles({ color, count = 20 }: { color: string; count?: number }) {
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1,
      duration: Math.random() * 15 + 10,
      delay: Math.random() * 5,
      opacity: Math.random() * 0.3 + 0.1,
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
            backgroundColor: color,
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

// ─── Glow Orbs ───────────────────────────────────────────────────────────────

function GlowOrbs({ color, glow }: { color: string; glow: string }) {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <motion.div
        className="absolute w-[300px] h-[300px] rounded-full blur-[100px]"
        style={{ backgroundColor: glow, top: '10%', left: '10%' }}
        animate={{
          x: [0, 60, -30, 40, 0],
          y: [0, -40, 20, -30, 0],
          scale: [1, 1.2, 0.9, 1.1, 1],
          opacity: [0.3, 0.5, 0.25, 0.4, 0.3],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute w-[200px] h-[200px] rounded-full blur-[80px]"
        style={{ backgroundColor: glow, bottom: '15%', right: '15%' }}
        animate={{
          x: [0, -50, 30, -20, 0],
          y: [0, 30, -40, 20, 0],
          scale: [0.8, 1.1, 0.9, 1.2, 0.8],
          opacity: [0.2, 0.4, 0.2, 0.35, 0.2],
        }}
        transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
      />
      <motion.div
        className="absolute w-[150px] h-[150px] rounded-full blur-[60px]"
        style={{ backgroundColor: 'rgba(253, 218, 36, 0.15)', top: '50%', left: '50%' }}
        animate={{
          x: [0, 40, -40, 0],
          y: [0, -30, 30, 0],
          opacity: [0.15, 0.25, 0.1, 0.15],
        }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 5 }}
      />
    </div>
  )
}

// ─── Grid Background ─────────────────────────────────────────────────────────

function GridBackground({ color }: { color: string }) {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {/* Perspective grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `
            linear-gradient(${color} 1px, transparent 1px),
            linear-gradient(90deg, ${color} 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />
      {/* Scan line */}
      <motion.div
        className="absolute left-0 right-0 h-[1px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          opacity: 0.15,
        }}
        animate={{ y: ['-10%', '110%'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

// ─── Code Rain (Matrix-Style Background) ─────────────────────────────────────

function CodeRain({ color }: { color: string }) {
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
            color: color,
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

// ─── Progress Ring ───────────────────────────────────────────────────────────

function ProgressRing({ progress, color, size = 80 }: { progress: number; color: string; size?: number }) {
  const radius = (size - 8) / 2
  const circumference = 2 * Math.PI * radius

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={3}
          fill="none"
        />
        {/* Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={3}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          animate={{ strokeDashoffset: circumference * (1 - progress) }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      {/* Percentage */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.span
          className="text-sm font-mono font-bold"
          style={{ color }}
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

// ─── Step Indicator ──────────────────────────────────────────────────────────

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
                  ? `${step.color}15`
                  : isComplete
                  ? `${step.color}08`
                  : 'transparent',
              }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className="flex items-center justify-center w-5 h-5 rounded-md"
                animate={{
                  backgroundColor: isActive ? `${step.color}25` : 'transparent',
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
                    <Check className="w-3 h-3" style={{ color: step.color }} />
                  </motion.div>
                ) : (
                  <Icon
                    className="w-3 h-3"
                    style={{ color: isActive ? step.color : 'var(--muted)' }}
                  />
                )}
              </motion.div>
              {isActive && (
                <motion.span
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 'auto', opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  className="text-[10px] font-medium whitespace-nowrap overflow-hidden"
                  style={{ color: step.color }}
                >
                  {step.label}
                </motion.span>
              )}
            </motion.div>
            {i < steps.length - 1 && (
              <motion.div
                className="w-4 h-[1px] mx-0.5"
                animate={{
                  backgroundColor: i < currentIndex ? step.color : 'rgba(255,255,255,0.08)',
                }}
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

function CodeEditorWindow({
  lines,
  stepColor,
  stepLabel,
}: {
  lines: string[]
  stepColor: string
  stepLabel: string
}) {
  const { displayedLines, cursorLine, cursorChar } = useTypingEffect(lines, 25)
  const editorRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.scrollTop = editorRef.current.scrollHeight
    }
  }, [displayedLines])

  return (
    <motion.div
      className="relative rounded-xl overflow-hidden border border-white/[0.06] bg-[#0d0d12]/90 backdrop-blur-xl shadow-2xl"
      initial={{ y: 20, opacity: 0, scale: 0.97 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: -20, opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
    >
      {/* Title Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
          </div>
          <div className="flex items-center gap-1.5 ml-3">
            <Terminal className="w-3 h-3" style={{ color: stepColor }} />
            <span className="text-[11px] font-mono" style={{ color: stepColor }}>
              {stepLabel}
            </span>
          </div>
        </div>
        <motion.div
          className="flex items-center gap-1.5"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: stepColor }} />
          <span className="text-[10px] text-white/30 font-mono">live</span>
        </motion.div>
      </div>

      {/* Code Content */}
      <div
        ref={editorRef}
        className="p-4 font-mono text-[12px] leading-[1.7] overflow-y-auto max-h-[300px] min-h-[240px]"
        style={{ scrollBehavior: 'smooth' }}
      >
        {displayedLines.map((line, i) => (
          <div key={i} className="flex">
            {/* Line number */}
            <span className="inline-block w-8 text-right mr-4 text-white/15 select-none text-[11px]">
              {i + 1}
            </span>
            {/* Code */}
            <span className="flex-1">
              {highlightCode(line || '', stepColor)}
              {/* Cursor */}
              {i === cursorLine && (
                <motion.span
                  className="inline-block w-[2px] h-[14px] ml-[1px] align-middle rounded-full"
                  style={{ backgroundColor: stepColor }}
                  animate={{ opacity: [1, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity }}
                />
              )}
            </span>
          </div>
        ))}
        {/* Empty lines for spacing */}
        {displayedLines.length === 0 && (
          <div className="flex">
            <span className="inline-block w-8 text-right mr-4 text-white/15 select-none text-[11px]">1</span>
            <motion.span
              className="inline-block w-[2px] h-[14px] rounded-full"
              style={{ backgroundColor: stepColor }}
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity }}
            />
          </div>
        )}
      </div>

      {/* Bottom glow line */}
      <motion.div
        className="h-[1px]"
        style={{
          background: `linear-gradient(90deg, transparent, ${stepColor}, transparent)`,
        }}
        animate={{ opacity: [0.3, 0.7, 0.3] }}
        transition={{ duration: 2, repeat: Infinity }}
      />
    </motion.div>
  )
}

// ─── Build Log Terminal ──────────────────────────────────────────────────────

function BuildLogTerminal({ logs, color }: { logs: string[]; color: string }) {
  const lastLogs = logs.slice(-3)

  return (
    <motion.div
      className="rounded-lg border border-white/[0.04] bg-black/40 backdrop-blur-sm px-3 py-2 overflow-hidden"
      initial={{ y: 10, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.3, duration: 0.4 }}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <div className="w-1 h-1 rounded-full" style={{ backgroundColor: color }} />
        <span className="text-[9px] uppercase tracking-wider text-white/20 font-mono">output</span>
      </div>
      <AnimatePresence mode="popLayout">
        {lastLogs.map((log, i) => (
          <motion.p
            key={log + i}
            className="text-[10px] font-mono text-white/40 truncate"
            initial={{ y: 8, opacity: 0 }}
            animate={{ y: 0, opacity: i === lastLogs.length - 1 ? 0.6 : 0.25 }}
            exit={{ y: -8, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <span style={{ color }} className="mr-1.5">›</span>
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
    <div className="relative flex h-full flex-col items-center justify-center overflow-hidden bg-[#08080c]">
      {/* Background Layers */}
      <GridBackground color={isError ? '#e5484d' : currentStep.color} />
      <CodeRain color={isError ? '#e5484d' : currentStep.color} />
      <GlowOrbs color={isError ? '#e5484d' : currentStep.color} glow={isError ? 'rgba(229, 72, 77, 0.3)' : currentStep.glow} />
      <FloatingParticles color={isError ? '#e5484d' : currentStep.color} count={15} />

      {/* Vignette overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 40%, #08080c 100%)',
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
          <ProgressRing
            progress={progress}
            color={isError ? '#e5484d' : currentStep.color}
            size={72}
          />
          <div>
            <AnimatePresence mode="wait">
              <motion.h2
                key={currentStep.id}
                className="text-lg font-semibold tracking-tight"
                style={{ color: isError ? '#e5484d' : currentStep.color }}
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
                className="text-xs text-white/40 mt-0.5"
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
              stepColor={currentStep.color}
              stepLabel={currentStep.label}
            />
          </AnimatePresence>
        )}

        {/* Error Display */}
        {isError && error && (
          <motion.div
            className="w-full rounded-xl border border-red-500/20 bg-red-500/5 backdrop-blur-xl p-4"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <span className="text-sm font-medium text-red-400">Error Details</span>
            </div>
            <p className="text-xs font-mono text-red-300/70">{error}</p>
          </motion.div>
        )}

        {/* Build Logs */}
        {buildLogs.length > 0 && !isError && (
          <div className="w-full">
            <BuildLogTerminal logs={buildLogs} color={currentStep.color} />
          </div>
        )}
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-[#08080c] to-transparent pointer-events-none" />
    </div>
  )
}
