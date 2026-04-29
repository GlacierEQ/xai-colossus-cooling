export interface AspenAuditEvent {
  event_id: string
  event_type: string
  ts: string
  message_id: string
  source: string
  summary: string
  payload?: Record<string, unknown>
}

function makeId(prefix: string): string {
  const now = new Date()
  const stamp = now.toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
  const rand = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${stamp}_${rand}`
}

export function createAspenAuditEvent(
  event_type: string,
  message_id: string,
  source: string,
  summary: string,
  payload?: Record<string, unknown>,
): AspenAuditEvent {
  return {
    event_id: makeId('evt_m2a'),
    event_type,
    ts: new Date().toISOString(),
    message_id,
    source,
    summary,
    payload,
  }
}

export function createRoutingAuditTrail(
  message_id: string,
  source: string,
  selectedCount: number,
  suppressedCount: number,
) {
  const issued = createAspenAuditEvent(
    'm2a_broadcast_issued',
    message_id,
    source,
    'M2A or MCP-to-All request issued to routing layer',
  )

  const selected = createAspenAuditEvent(
    'm2a_responders_selected',
    message_id,
    source,
    'Relevant responders selected by routing layer',
    {
      selected_responders: selectedCount,
      suppressed_responders: suppressedCount,
    },
  )

  const bundled = createAspenAuditEvent(
    'm2a_bundle_emitted',
    message_id,
    source,
    'Response bundle emitted from routing layer',
    {
      selected_responders: selectedCount,
      suppressed_responders: suppressedCount,
    },
  )

  return { issued, selected, bundled }
}
