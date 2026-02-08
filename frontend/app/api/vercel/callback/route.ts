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

function popupHtml(origin: string, payload: Record<string, unknown>, autoClose: boolean) {
  const json = JSON.stringify(payload).replace(/</g, '\\u003c')
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Vercel Connect</title>
  </head>
  <body>
    <script>
      (function () {
        try {
          if (window.opener && !window.opener.closed) {
            window.opener.postMessage(${json}, ${JSON.stringify(origin)});
          }
        } catch (e) {}
        ${autoClose ? "setTimeout(function () { window.close(); }, 150);" : ""}
      })();
    </script>
    <div style="font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto; padding: 16px;">
      <h3 style="margin:0 0 8px 0;">Vercel Connect</h3>
      <pre style="white-space: pre-wrap; background:#111827; color:#e5e7eb; padding:12px; border-radius:8px; font-size:12px;">${json}</pre>
      ${autoClose ? "<p style=\"color:#6b7280; font-size:12px;\">Connected. You can close this window.</p>" : "<p style=\"color:#b91c1c; font-size:12px;\">Connection failed. This window will stay open so you can copy the error.</p>"}
    </div>
  </body>
</html>`
}

export async function GET(req: NextRequest) {
  const clientId = process.env.VERCEL_OAUTH_CLIENT_ID
  const clientSecret = process.env.VERCEL_OAUTH_CLIENT_SECRET
  const redirectUri =
    process.env.VERCEL_OAUTH_REDIRECT_URI || `${req.nextUrl.origin}/api/vercel/callback`

  if (!clientId || !clientSecret) {
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: 'Missing VERCEL_OAUTH_CLIENT_ID or VERCEL_OAUTH_CLIENT_SECRET',
    }, false)
    return new NextResponse(html, { status: 500, headers: { 'Content-Type': 'text/html' } })
  }

  const url = new URL(req.url)
  const code = url.searchParams.get('code')
  const state = url.searchParams.get('state')

  if (!code || !state) {
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: 'Missing code or state',
    }, false)
    return new NextResponse(html, { status: 400, headers: { 'Content-Type': 'text/html' } })
  }

  const cookieStore = await cookies()
  const storedState = cookieStore.get('vercel_oauth_state')?.value
  const codeVerifier = cookieStore.get('vercel_oauth_code_verifier')?.value

  if (!storedState || storedState !== state) {
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: 'State mismatch',
    }, false)
    return new NextResponse(html, { status: 400, headers: { 'Content-Type': 'text/html' } })
  }
  if (!codeVerifier) {
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: 'Missing code verifier',
    }, false)
    return new NextResponse(html, { status: 400, headers: { 'Content-Type': 'text/html' } })
  }

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: clientId,
    code,
    code_verifier: codeVerifier,
    redirect_uri: redirectUri,
  })

  // Many Vercel OAuth apps use client_secret_basic by default.
  // Use HTTP Basic auth so token exchange succeeds regardless of client auth mode.
  const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString('base64')
  const tokenResp = await fetch('https://api.vercel.com/login/oauth/token', {
    method: 'POST',
    headers: {
      Authorization: `Basic ${credentials}`,
    },
    body,
  })

  if (!tokenResp.ok) {
    const txt = await tokenResp.text()
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: `Token exchange failed (${tokenResp.status}): ${txt.slice(0, 2000)}`,
    }, false)
    return new NextResponse(html, { status: 500, headers: { 'Content-Type': 'text/html' } })
  }

  const tokenData = (await tokenResp.json()) as TokenResponse
  if (!tokenData.access_token) {
    const html = popupHtml(req.nextUrl.origin, {
      type: 'vercel_oauth_complete',
      success: false,
      error: 'No access_token returned',
    }, false)
    return new NextResponse(html, { status: 500, headers: { 'Content-Type': 'text/html' } })
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

  const html = popupHtml(req.nextUrl.origin, {
    type: 'vercel_oauth_complete',
    success: true,
  }, true)
  return new NextResponse(html, { status: 200, headers: { 'Content-Type': 'text/html' } })
}

