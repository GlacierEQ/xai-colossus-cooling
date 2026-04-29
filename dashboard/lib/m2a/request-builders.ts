import type { M2ARequestEnvelope } from './relevance-router'

function makeMessageId(prefix: string): string {
  const stamp = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
  const rand = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${stamp}_${rand}`
}

export function requestForecastEnvelope(zoneId = 'ZONE-001'): M2ARequestEnvelope {
  return {
    message_id: makeMessageId('m2a_forecast'),
    protocol: 'mcp_to_all',
    intent: 'request_forecast',
    source: 'dashboard_control_surface',
    target_scope: 'broadcast',
    domains: ['analytics', 'forecast', 'cooling'],
    required_capabilities: ['request_forecast'],
    context: {
      zone_id: zoneId,
      lookahead_steps: 3,
    },
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
      priority: 'high',
    },
  }
}

export function requestZoneSnapshotEnvelope(zoneId = 'ZONE-001'): M2ARequestEnvelope {
  return {
    message_id: makeMessageId('m2a_zone_snapshot'),
    protocol: 'mcp_to_all',
    intent: 'request_zone_snapshot',
    source: 'dashboard_control_surface',
    target_scope: 'broadcast',
    domains: ['runtime', 'telemetry', 'cooling'],
    required_capabilities: ['request_zone_snapshot'],
    context: {
      zone_id: zoneId,
    },
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
