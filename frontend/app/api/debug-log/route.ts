// #region agent log — temporary debug endpoint
import { NextResponse } from 'next/server'
import { appendFileSync } from 'fs'

const LOG_PATH = '/Users/saikarthik/Desktop/Projects/workspace/halo/.cursor/debug.log'

export async function POST(req: Request) {
  try {
    const payload = await req.json()
    appendFileSync(LOG_PATH, JSON.stringify(payload) + '\n')
    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 })
  }
}
// #endregion
