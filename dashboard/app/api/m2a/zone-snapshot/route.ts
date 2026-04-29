import { NextResponse } from 'next/server'

import { requestZoneSnapshotEnvelope } from '../../../../lib/m2a/request-builders'
import { executeM2ARoute } from '../../../../lib/m2a/route-runtime'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const zoneId = searchParams.get('zone_id') || 'ZONE-001'

  try {
    const result = await executeM2ARoute(requestZoneSnapshotEnvelope(zoneId))
    return NextResponse.json(result)
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to build zone snapshot bundle',
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
