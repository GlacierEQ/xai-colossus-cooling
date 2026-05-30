import { describe, expect, it } from 'vitest'

import { validateResponder, validateResponderRegistry } from './registry-validation'

describe('M2A responder registry validation', () => {
  it('accepts a valid responder', () => {
    const result = validateResponder({
      node_id: 'apex_orchestrator_runtime',
      node_type: 'runtime_orchestrator',
      capabilities: ['request_zone_snapshot'],
      domains: ['runtime', 'cooling'],
      accepts_broadcast: true,
      priority: 9,
      effectiveness_score: 0.92,
      current_load: 0.33,
    })

    expect(result.valid).toBe(true)
    expect(result.errors).toHaveLength(0)
  })

  it('rejects invalid score and load values', () => {
    const result = validateResponder({
      node_id: 'bad_node',
      node_type: 'runtime_orchestrator',
      capabilities: ['request_zone_snapshot'],
      domains: ['runtime'],
      accepts_broadcast: true,
      effectiveness_score: 1.5,
      current_load: -0.1,
    })

    expect(result.valid).toBe(false)
    expect(result.errors.some(error => error.includes('effectiveness_score'))).toBe(true)
    expect(result.errors.some(error => error.includes('current_load'))).toBe(true)
  })

  it('rejects a malformed registry', () => {
    const result = validateResponderRegistry([
      {
        node_id: 'ok_node',
        node_type: 'analytics_connector',
        capabilities: ['request_forecast'],
        domains: ['analytics'],
        accepts_broadcast: true,
      },
      {
        node_id: '',
        node_type: 'broken_node',
        capabilities: [],
        domains: [],
        accepts_broadcast: true,
      },
    ])

    expect(result.valid).toBe(false)
    expect(result.errors.length > 0).toBe(true)
  })
})
