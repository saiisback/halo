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
