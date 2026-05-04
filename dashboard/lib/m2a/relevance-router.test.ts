import { describe, expect, it } from 'vitest'

import { buildResponseBundle, scoreResponder, type CapabilityRegistration, type M2ARequestEnvelope } from './relevance-router'

const baseEnvelope: M2ARequestEnvelope = {
  message_id: 'msg_test_001',
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

const analyticsResponder: CapabilityRegistration = {
  node_id: 'motherduck_analytics_connector',
  node_type: 'analytics_connector',
  capabilities: ['request_forecast', 'query_hot_zones'],
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
}

describe('M2A relevance router', () => {
  it('scores a healthy matching responder', () => {
    const ranked = scoreResponder(baseEnvelope, analyticsResponder)
    expect(ranked).not.toBeNull()
    expect(ranked?.node_id).toBe('motherduck_analytics_connector')
    expect(ranked?.timeout_ms).toBe(800)
    expect((ranked?.relevance ?? 0) > 0.5).toBe(true)
  })

  it('suppresses degraded responders', () => {
    const degraded = { ...analyticsResponder, status: 'degraded' as const }
    const ranked = scoreResponder(baseEnvelope, degraded)
    expect(ranked).toBeNull()
  })

  it('suppresses overloaded responders', () => {
    const overloaded = { ...analyticsResponder, current_load: 0.99 }
    const ranked = scoreResponder(baseEnvelope, overloaded)
    expect(ranked).toBeNull()
  })

  it('filters by pillar target when pillar scope is used', () => {
    const pillarEnvelope: M2ARequestEnvelope = {
      ...baseEnvelope,
      target_scope: 'pillar',
      target: 'analytics_forecast_pillar',
    }

    const wrongPillar = { ...analyticsResponder, pillar: 'runtime_orchestration_pillar' }
    expect(scoreResponder(pillarEnvelope, wrongPillar)).toBeNull()
    expect(scoreResponder(pillarEnvelope, analyticsResponder)?.pillar).toBe('analytics_forecast_pillar')
  })

  it('returns a ranked bundle with selected responders', () => {
    const responders: CapabilityRegistration[] = [
      analyticsResponder,
      {
        ...analyticsResponder,
        node_id: 'backup_forecast_node',
        effectiveness_score: 0.65,
        current_load: 0.21,
      },
    ]

    const bundle = buildResponseBundle(baseEnvelope, responders)
    expect(bundle.bundle_status).toBe('complete')
    expect(bundle.selected_responders.length).toBe(2)
    expect(bundle.selected_responders[0].relevance >= bundle.selected_responders[1].relevance).toBe(true)
  })
})
