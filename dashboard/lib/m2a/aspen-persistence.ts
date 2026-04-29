import type { AspenAuditEvent } from './aspen-audit'

export interface AspenPersistenceResult {
  mode: 'webhook' | 'offline'
  persisted: boolean
  event_count: number
  target?: string
}

export async function persistAspenAuditEvents(
  events: AspenAuditEvent[],
): Promise<AspenPersistenceResult> {
  const webhookUrl = process.env.ASPEN_AUDIT_WEBHOOK_URL || ''

  if (!webhookUrl) {
    return {
      mode: 'offline',
      persisted: false,
      event_count: events.length,
    }
  }

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify({ events }),
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`Aspen audit persistence failed: ${response.status}`)
  }

  return {
    mode: 'webhook',
    persisted: true,
    event_count: events.length,
    target: webhookUrl,
  }
}
