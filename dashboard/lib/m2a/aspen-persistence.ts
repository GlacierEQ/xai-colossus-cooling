import type { AspenAuditEvent } from './aspen-audit'

export interface AspenPersistenceResult {
  mode: 'connector' | 'webhook' | 'offline'
  persisted: boolean
  event_count: number
  target?: string
}

async function persistViaConnector(events: AspenAuditEvent[]): Promise<AspenPersistenceResult> {
  const connectorUrl = process.env.ASPEN_CONNECTOR_URL || ''
  const connectorToken = process.env.ASPEN_CONNECTOR_TOKEN || ''

  const response = await fetch(connectorUrl, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      ...(connectorToken ? { authorization: `Bearer ${connectorToken}` } : {}),
    },
    body: JSON.stringify({ events, source: 'm2a_route_runtime' }),
    cache: 'no-store',
  })

  if (!response.ok) {
    throw new Error(`Aspen connector persistence failed: ${response.status}`)
  }

  return {
    mode: 'connector',
    persisted: true,
    event_count: events.length,
    target: connectorUrl,
  }
}

async function persistViaWebhook(events: AspenAuditEvent[]): Promise<AspenPersistenceResult> {
  const webhookUrl = process.env.ASPEN_AUDIT_WEBHOOK_URL || ''

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

export async function persistAspenAuditEvents(
  events: AspenAuditEvent[],
): Promise<AspenPersistenceResult> {
  const connectorUrl = process.env.ASPEN_CONNECTOR_URL || ''
  const webhookUrl = process.env.ASPEN_AUDIT_WEBHOOK_URL || ''

  if (connectorUrl) {
    return persistViaConnector(events)
  }

  if (webhookUrl) {
    return persistViaWebhook(events)
  }

  return {
    mode: 'offline',
    persisted: false,
    event_count: events.length,
  }
}
