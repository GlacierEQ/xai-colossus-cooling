import { NextRequest, NextResponse } from 'next/server'

const COLOSSUS_API_URL = process.env.COLOSSUS_API_URL || 'http://localhost:3000'
const COLOSSUS_API_KEY = process.env.COLOSSUS_API_KEY || ''

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get('x-api-key')
  if (authHeader !== COLOSSUS_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const res = await fetch(`${COLOSSUS_API_URL}/api/health`, {
      headers: { Authorization: `Bearer ${COLOSSUS_API_KEY}` }
    })
    const data = await res.json()
    return NextResponse.json({ ...data, dashboard: 'live' })
  } catch {
    return NextResponse.json({ status: 'colossus_unreachable', dashboard: 'live' })
  }
}
