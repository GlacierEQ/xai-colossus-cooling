import { NextResponse } from 'next/server'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

import { createRoutingAuditTrail } from '../../../../lib/m2a/aspen-audit'
import { persistAspenAuditEvents } from '../../../../lib/m2a/aspen-persistence'
import { buildResponseBundle } from '../../../../lib/m2a/relevance-router'
import { requestZoneSnapshotEnvelope } from '../../../../lib/m2a/request-builders'

async function loadResponderRegistry() {
  const registryPath = path.join(process.cwd(), '..', 'config', 'm2a', 'responder-registry.json')
  const content = await readFile(registryPath, 'utf-8')
  return JSON.parse(content)
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const zoneId = searchParams.get('zone_id') || 'ZONE-001'

  try {
    const responders = await loadResponderRegistry()
    const envelope = requestZoneSnapshotEnvelope(zoneId)
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
        error: 'Failed to build zone snapshot bundle',
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
