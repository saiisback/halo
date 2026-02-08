const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface GenerateRequest {
  prompt: string
  network?: string
  user_wallet?: string
}

export interface BuildEvent {
  step: string
  message?: string
  log?: string
  contract_id?: string
  files?: Record<string, string>
  status?: string
  error?: string
  // Analysis metadata (emitted during the "analyzing" step)
  template_type?: string
  spec?: Record<string, unknown>
}

/**
 * Generate a DApp from a natural language prompt
 * Returns an async generator that yields build events
 */
export async function* generateDApp(
  request: GenerateRequest
): AsyncGenerator<BuildEvent> {
  const response = await fetch(`${API_URL}/api/v1/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      prompt: request.prompt,
      network: request.network || 'testnet',
      user_wallet: request.user_wallet,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    
    // Parse SSE events
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data) {
          try {
            const event: BuildEvent = JSON.parse(data)
            yield event
          } catch (e) {
            console.error('Failed to parse event:', e)
          }
        }
      }
    }
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`)
    return response.ok
  } catch {
    return false
  }
}

// ---------------------------------------------------------------------------
// Publish API (One-click Vercel publish)
// ---------------------------------------------------------------------------

export interface PublishRequest {
  contract_id: string
  files: Record<string, string>
  name?: string
  network?: string
}

export interface PublishResponse {
  success: boolean
  url?: string
  deployment_id?: string
  claim_url?: string
  transfer_code?: string
  error?: string
}

export async function publishToVercel(request: PublishRequest): Promise<PublishResponse> {
  const response = await fetch(`${API_URL}/api/v1/publish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contract_id: request.contract_id,
      files: request.files,
      name: request.name,
      network: request.network || 'testnet',
    }),
  })

  if (!response.ok) {
    let detail = `HTTP error! status: ${response.status}`
    try {
      const data = await response.json()
      if (data?.detail) detail = String(data.detail)
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return await response.json()
}

export async function publishClaimableToVercel(
  request: PublishRequest & { return_url: string }
): Promise<PublishResponse> {
  const response = await fetch(`${API_URL}/api/v1/publish/claim`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contract_id: request.contract_id,
      files: request.files,
      name: request.name,
      network: request.network || 'testnet',
      return_url: request.return_url,
    }),
  })

  if (!response.ok) {
    let detail = `HTTP error! status: ${response.status}`
    try {
      const data = await response.json()
      if (data?.detail) detail = String(data.detail)
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return await response.json()
}

// ---------------------------------------------------------------------------
// Protocols API
// ---------------------------------------------------------------------------

export interface Protocol {
  id: string
  name: string
  description: string
  category: string
  icon: string
  integration_prompt: string
  sdk_package?: string | null
  docs_url?: string | null
}

export interface SuggestedProtocol {
  id: string
  name: string
  description: string
  category: string
  icon: string
  reason: string
}

/**
 * Fetch the curated list of Stellar ecosystem protocols.
 * Optionally filter by category.
 */
export async function fetchProtocols(category?: string): Promise<Protocol[]> {
  try {
    const url = new URL(`${API_URL}/api/v1/protocols`)
    if (category) url.searchParams.set('category', category)
    const response = await fetch(url.toString())
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (e) {
    console.error('Failed to fetch protocols:', e)
    return []
  }
}

/**
 * Ask the AI to suggest protocols that complement the current DApp.
 */
export async function fetchSuggestedProtocols(
  templateType: string,
  contractSpec: Record<string, unknown>,
  currentProtocols: string[] = [],
): Promise<SuggestedProtocol[]> {
  try {
    const response = await fetch(`${API_URL}/api/v1/protocols/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        template_type: templateType,
        contract_spec: contractSpec,
        current_protocols: currentProtocols,
      }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return data.suggestions ?? []
  } catch (e) {
    console.error('Failed to fetch protocol suggestions:', e)
    return []
  }
}

/**
 * Fetch available protocol categories.
 */
export async function fetchProtocolCategories(): Promise<string[]> {
  try {
    const response = await fetch(`${API_URL}/api/v1/protocols/categories`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } catch (e) {
    console.error('Failed to fetch categories:', e)
    return []
  }
}
