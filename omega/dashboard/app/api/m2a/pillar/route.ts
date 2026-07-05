import { NextResponse } from 'next/server'

import type { M2ARequestEnvelope } from '../../../../lib/m2a/relevance-router'
import { executeM2ARoute } from '../../../../lib/m2a/route-runtime'

function requestPillarEnvelope(pillar: string): M2ARequestEnvelope {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
  return {
    message_id: `m2a_pillar_${stamp}`,
    protocol: 'mcp_to_all',
    intent: 'pillar_broadcast',
    source: 'dashboard_control_surface',
    target_scope: 'pillar',
    target: pillar,
    domains: ['runtime', 'analytics', 'memory', 'cooling'],
    routing: {
      mode: 'pillar_broadcast',
      max_responders: 5,
      suppress_irrelevant: true,
      bundle_strategy: 'rank_and_merge',
    },
    auth: {
      mode: 'api_key',
    },
    trace: {
      audit: true,
      priority: 'high',
    },
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const pillar = searchParams.get('pillar') || 'runtime_orchestration_pillar'

  try {
    const result = await executeM2ARoute(requestPillarEnvelope(pillar))
    return NextResponse.json(result)
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to build pillar bundle',
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
