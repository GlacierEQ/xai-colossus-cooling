import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('node:fs/promises', () => ({
  readFile: vi.fn(),
}))

vi.mock('./aspen-persistence', () => ({
  persistAspenAuditEvents: vi.fn(async (events: any[]) => ({
    mode: 'offline',
    persisted: false,
    event_count: events.length,
  })),
}))

import { readFile } from 'node:fs/promises'
import { executeM2ARoute } from './route-runtime'
import type { M2ARequestEnvelope } from './relevance-router'

const mockedReadFile = vi.mocked(readFile)

const envelope: M2ARequestEnvelope = {
  message_id: 'msg_runtime_001',
  protocol: 'mcp_to_all',
  intent: 'request_forecast',
  source: 'dashboard_control_surface',
  target_scope: 'broadcast',
  domains: ['analytics', 'forecast', 'cooling'],
  required_capabilities: ['request_forecast'],
  routing: {
    mode: 'relevance_filtered_broadcast',
    max_responders: 3,
    suppress_irrelevant: true,
    bundle_strategy: 'rank_and_merge',
  },
}

beforeEach(() => {
  mockedReadFile.mockReset()
})

describe('M2A route runtime', () => {
  it('loads, validates, bundles, and returns audit metadata', async () => {
    mockedReadFile.mockResolvedValueOnce(JSON.stringify([
      {
        node_id: 'motherduck_analytics_connector',
        node_type: 'analytics_connector',
        capabilities: ['request_forecast'],
        domains: ['analytics', 'forecast', 'cooling'],
        priority: 8,
        cost_class: 'medium',
        latency_class: 'normal',
        accepts_broadcast: true,
        response_mode: 'selective',
        pillar: 'analytics_forecast_pillar',
        effectiveness_score: 0.88,
        current_load: 0.42,
        status: 'healthy',
      },
    ]))

    const result = await executeM2ARoute(envelope)

    expect(result.registry_validation.valid).toBe(true)
    expect(result.bundle.bundle_status).toBe('complete')
    expect(result.bundle.selected_responders.length).toBe(1)
    expect(result.bundle.audit_event_id).toBeTruthy()
    expect(result.persistence.event_count).toBe(3)
  })

  it('fails cleanly on malformed registry', async () => {
    mockedReadFile.mockResolvedValueOnce(JSON.stringify([
      {
        node_id: '',
        node_type: 'broken',
        capabilities: [],
        domains: [],
        accepts_broadcast: true,
      },
    ]))

    await expect(executeM2ARoute(envelope)).rejects.toThrow(/Invalid responder registry/)
  })
})
