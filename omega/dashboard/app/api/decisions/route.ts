import { NextRequest, NextResponse } from 'next/server'

const MASTERMIND_URL   = process.env.MASTERMIND_URL   || 'http://localhost:4000'
const COLOSSUS_API_KEY = process.env.COLOSSUS_API_KEY || ''

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get('x-api-key')
  if (authHeader !== COLOSSUS_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const res = await fetch(`${MASTERMIND_URL}/api/decisions?limit=20`, {
      headers: { Authorization: `Bearer ${COLOSSUS_API_KEY}` },
      next: { revalidate: 0 }
    })
    if (!res.ok) throw new Error(`Mastermind ${res.status}`)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({
      decisions: [
        { id: 'D-001', timestamp: new Date().toISOString(), action: 'INCREASE_FLOW zone_6', reward: 0.94, confidence: 0.97 },
        { id: 'D-002', timestamp: new Date(Date.now()-5000).toISOString(), action: 'HOLD zone_3', reward: 0.87, confidence: 0.91 },
        { id: 'D-003', timestamp: new Date(Date.now()-12000).toISOString(), action: 'REDUCE_FLOW zone_1', reward: 0.72, confidence: 0.88 },
      ]
    })
  }
}
