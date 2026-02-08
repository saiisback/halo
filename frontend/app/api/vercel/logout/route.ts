import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

export async function POST() {
  const cookieStore = await cookies()
  const accessToken = cookieStore.get('vercel_access_token')?.value

  // Best-effort revoke (optional but nicer)
  const clientId = process.env.VERCEL_OAUTH_CLIENT_ID
  const clientSecret = process.env.VERCEL_OAUTH_CLIENT_SECRET
  if (accessToken && clientId && clientSecret) {
    try {
      const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString('base64')
      await fetch('https://api.vercel.com/login/oauth/token/revoke', {
        method: 'POST',
        headers: {
          Authorization: `Basic ${credentials}`,
        },
        body: new URLSearchParams({ token: accessToken }),
      })
    } catch {
      // ignore revoke errors, still logout locally
    }
  }

  // Clear cookies
  cookieStore.set('vercel_access_token', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_refresh_token', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_oauth_state', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_oauth_nonce', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_oauth_code_verifier', '', { maxAge: 0, path: '/' })

  return NextResponse.json({ success: true })
}

