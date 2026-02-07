import { NextResponse, type NextRequest } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

type PublishBody = {
  contract_id: string
  files: Record<string, string>
  name?: string
  network?: string
}

export async function POST(req: NextRequest) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const cookieStore = await cookies()
  const vercelToken = cookieStore.get('vercel_access_token')?.value

  if (!vercelToken) {
    return NextResponse.json({ error: 'Not connected to Vercel' }, { status: 401 })
  }

  let body: PublishBody
  try {
    body = (await req.json()) as PublishBody
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const resp = await fetch(`${backendUrl}/api/v1/publish`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Vercel-Access-Token': vercelToken,
    },
    body: JSON.stringify(body),
  })

  const text = await resp.text()
  return new NextResponse(text, {
    status: resp.status,
    headers: {
      'Content-Type': resp.headers.get('content-type') || 'application/json',
    },
  })
}

