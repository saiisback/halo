import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('vercel_access_token')?.value
  return NextResponse.json({ connected: !!token })
}

