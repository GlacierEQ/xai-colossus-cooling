import { NextResponse } from 'next/server'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

import { createRoutingAuditTrail } from '../../../../lib/m2a/aspen-audit'
import { persistAspenAuditEvents } from '../../../../lib/m2a/aspen-persistence'
import { buildResponseBundle } from '../../../../lib/m2a/relevance-router'
import type { M2ARequestEnvelope } from '../../../../lib/m2a/relevance-router'

async function loadResponderRegistry() {
  const registryPath = path.join(process.cwd(), '..', 'config', 'm2a', 'responder-registry.json')
  const content = await readFile(registryPath, 'utf-8')
  return JSON.parse(content)
}

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
    const responders = await loadResponderRegistry()
    const envelope = requestPistonStatusEnvelope()
    const bundle = buildResponseBundle(envelope, responders)
    const audit = createRoutingAuditTrail(
      envelope.message_id,
      envelope.source,
      bundle.selected_responders.length,
      bundle.suppressed_responders,
    )
    const persistence = await persistAspenAuditEvents([
      audit.issued,
      audit.selected,
      audit.bundled,
    ])

    return NextResponse.json({
      envelope,
      bundle: {
        ...bundle,
        audit_event_id: audit.bundled.event_id,
      },
      audit,
      persistence,
    })
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
