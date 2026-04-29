import { NextResponse } from 'next/server'

import type { M2ARequestEnvelope } from '../../../../lib/m2a/relevance-router'
import { executeM2ARoute } from '../../../../lib/m2a/route-runtime'

function requestPistonStatusEnvelope(): M2ARequestEnvelope {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
  return {
    message_id: `m2a_piston_status_${stamp}`,
    protocol: 'mcp_to_all',
    intent: 'request_piston_status',
    source: 'dashboard_control_surface',
    target_scope: 'broadcast',
    domains: ['runtime', 'audit', 'cooling'],
    required_capabilities: ['request_piston_status'],
    routing: {
      mode: 'relevance_filtered_broadcast',
      max_responders: 3,
      suppress_irrelevant: true,
      bundle_strategy: 'rank_and_merge',
    },
    auth: {
      mode: 'api_key',
    },
    trace: {
      audit: true,
      priority: 'normal',
    },
  }
}

export async function GET() {
  try {
    const result = await executeM2ARoute(requestPistonStatusEnvelope())
    return NextResponse.json(result)
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to build piston status bundle',
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
