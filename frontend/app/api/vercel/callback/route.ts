import { NextResponse, type NextRequest } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

type TokenResponse = {
  access_token: string
  token_type: string
  expires_in: number
  scope?: string
  refresh_token?: string
  id_token?: string
}

export async function GET(req: NextRequest) {
  const clientId = process.env.VERCEL_OAUTH_CLIENT_ID
  const clientSecret = process.env.VERCEL_OAUTH_CLIENT_SECRET
  const redirectUri = process.env.VERCEL_OAUTH_REDIRECT_URI

  if (!clientId || !clientSecret || !redirectUri) {
    return NextResponse.json(
      { error: 'Missing Vercel OAuth env vars (client id/secret/redirect uri)' },
      { status: 500 }
    )
  }

  const url = new URL(req.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')

  if (!code || !state) {
    return NextResponse.json({ error: 'Missing code or state' }, { status: 400 })
  }

  const cookieStore = await cookies()
  const storedState = cookieStore.get('vercel_oauth_state')?.value
  const codeVerifier = cookieStore.get('vercel_oauth_code_verifier')?.value

  if (!storedState || storedState !== state) {
    return NextResponse.json({ error: 'State mismatch' }, { status: 400 })
  }
  if (!codeVerifier) {
    return NextResponse.json({ error: 'Missing code verifier' }, { status: 400 })
  }

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: clientId,
    client_secret: clientSecret,
    code,
    code_verifier: codeVerifier,
    redirect_uri: redirectUri,
  })

  const tokenResp = await fetch('https://api.vercel.com/login/oauth/token', {
    method: 'POST',
    body,
  })

  if (!tokenResp.ok) {
    const txt = await tokenResp.text()
    return NextResponse.json(
      { error: `Token exchange failed (${tokenResp.status}): ${txt.slice(0, 2000)}` },
      { status: 500 }
    )
  }

  const tokenData = (await tokenResp.json()) as TokenResponse
  if (!tokenData.access_token) {
    return NextResponse.json({ error: 'No access_token returned' }, { status: 500 })
  }

  // Store tokens in httpOnly cookies (same-site with the deployed frontend)
  cookieStore.set('vercel_access_token', tokenData.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: tokenData.expires_in ?? 3600,
    path: '/',
  })
  if (tokenData.refresh_token) {
    cookieStore.set('vercel_refresh_token', tokenData.refresh_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 30,
      path: '/',
    })
  }

  // Clear short-lived oauth cookies
  cookieStore.set('vercel_oauth_state', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_oauth_nonce', '', { maxAge: 0, path: '/' })
  cookieStore.set('vercel_oauth_code_verifier', '', { maxAge: 0, path: '/' })

  return NextResponse.json({ success: true })
}

