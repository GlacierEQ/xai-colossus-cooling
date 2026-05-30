import { NextRequest, NextResponse } from 'next/server'

const COLOSSUS_API_URL = process.env.COLOSSUS_API_URL || 'http://localhost:3000'
const COLOSSUS_API_KEY = process.env.COLOSSUS_API_KEY || ''

export async function GET(req: NextRequest) {
  const authHeader = req.headers.get('x-api-key')
  if (authHeader !== COLOSSUS_API_KEY) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const res = await fetch(`${COLOSSUS_API_URL}/api/thermal/snapshot`, {
      headers: { Authorization: `Bearer ${COLOSSUS_API_KEY}` },
      next: { revalidate: 0 }
    })
    if (!res.ok) throw new Error(`Colossus ${res.status}`)
    return NextResponse.json(await res.json())
  } catch (e: any) {
    // Return mock data so the dashboard renders even without a live Colossus
    return NextResponse.json({
      status: 'MOCK', timestamp: new Date().toISOString(),
      zones: Object.fromEntries(
        Array.from({length: 6}, (_, i) => [
          `zone_${i+1}`, { temp_c: 44 + i * 3.2, status: i < 5 ? 'nominal' : 'warm' }
        ])
      ),
      pistons: Object.fromEntries(
        Array.from({length: 12}, (_, i) => [
          `piston_${i+1}`, { state: i % 4 === 0 ? 'active' : 'idle', flow_rate: i % 4 === 0 ? 8.4 : 0 }
        ])
      ),
      morpheus_active: true
    })
  }
}
