import crypto from 'node:crypto'
import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

function base64Url(buf: Buffer) {
  return buf
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
}

function randomString(bytes = 32) {
  return base64Url(crypto.randomBytes(bytes))
}

export async function GET() {
  const clientId = process.env.VERCEL_OAUTH_CLIENT_ID
  const redirectUri = process.env.VERCEL_OAUTH_REDIRECT_URI

  if (!clientId || !redirectUri) {
    return NextResponse.json(
      { error: 'Missing VERCEL_OAUTH_CLIENT_ID or VERCEL_OAUTH_REDIRECT_URI' },
      { status: 500 }
    )
  }

  // PKCE (required by Vercel)
  const state = randomString(32)
  const nonce = randomString(32)
  const codeVerifier = randomString(32)
  const codeChallenge = base64Url(crypto.createHash('sha256').update(codeVerifier).digest())

  const cookieStore = await cookies()
  cookieStore.set('vercel_oauth_state', state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 10 * 60,
    path: '/',
  })
  cookieStore.set('vercel_oauth_nonce', nonce, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 10 * 60,
    path: '/',
  })
  cookieStore.set('vercel_oauth_code_verifier', codeVerifier, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 10 * 60,
    path: '/',
  })

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email profile offline_access',
    state,
    nonce,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    // Popup flow: Vercel will postMessage the response to opener
    response_mode: 'web_message.opener',
  })

  const authorizationUrl = `https://vercel.com/oauth/authorize?${params.toString()}`
  return NextResponse.json({ authorizationUrl })
}

