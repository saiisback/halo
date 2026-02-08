import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('vercel_access_token')?.value

  if (!token) {
    return NextResponse.json({ connected: false }, { status: 401 })
  }

  // Prefer the OAuth userinfo endpoint (works with Sign in with Vercel scopes)
  const userInfo = await fetch('https://api.vercel.com/login/oauth/userinfo', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (userInfo.ok) {
    const data = await userInfo.json()
    return NextResponse.json({
      connected: true,
      id: data?.sub ?? null,
      username: data?.preferred_username ?? null,
      name: data?.name ?? null,
      email: data?.email ?? null,
      avatar: data?.picture ?? null,
    })
  }

  // Fallback: Vercel REST API user endpoint (may require additional permissions)
  const resp = await fetch('https://api.vercel.com/v2/user', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!resp.ok) {
    // If token is invalid/expired or permissions missing, treat as disconnected.
    if (resp.status === 401 || resp.status === 403) {
      cookieStore.set('vercel_access_token', '', { maxAge: 0, path: '/' })
      cookieStore.set('vercel_refresh_token', '', { maxAge: 0, path: '/' })
      return NextResponse.json(
        { connected: false, error: `Vercel token not authorized (${resp.status})` },
        { status: 401 }
      )
    }

    const txt = await resp.text()
    return NextResponse.json(
      { connected: true, error: `Failed to fetch user (${resp.status}): ${txt.slice(0, 1000)}` },
      { status: 500 }
    )
  }

  const data = await resp.json()
  return NextResponse.json({
    connected: true,
    id: data?.user?.id ?? data?.id ?? null,
    username: data?.user?.username ?? data?.username ?? null,
    name: data?.user?.name ?? data?.name ?? null,
    email: data?.user?.email ?? data?.email ?? null,
    avatar: data?.user?.avatar ?? data?.avatar ?? null,
  })
}

