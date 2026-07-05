export type RoutingMode = 'direct' | 'relevance_filtered_broadcast' | 'pillar_broadcast'
export type BundleStrategy = 'first' | 'rank_and_merge' | 'rank_only'

export interface M2ARequestEnvelope {
  message_id: string
  protocol: 'm2a' | 'mcp_to_all'
  intent: string
  source: string
  target_scope: 'single' | 'pillar' | 'broadcast'
  target?: string
  domains?: string[]
  required_capabilities?: string[]
  context?: Record<string, unknown>
  routing?: {
    mode?: RoutingMode
    max_responders?: number
    suppress_irrelevant?: boolean
    bundle_strategy?: BundleStrategy
  }
  trace?: {
    session_id?: string
    audit?: boolean
    priority?: 'low' | 'normal' | 'high' | 'critical'
  }
}

export interface CapabilityRegistration {
  node_id: string
  node_type: string
  capabilities: string[]
  domains: string[]
  priority?: number
  cost_class?: 'low' | 'medium' | 'high'
  latency_class?: 'fast' | 'normal' | 'slow'
  accepts_broadcast: boolean
  response_mode?: 'direct' | 'selective' | 'bundle_only'
  pillar?: string
  effectiveness_score?: number
  current_load?: number
  status?: 'healthy' | 'degraded' | 'offline'
}

export interface RankedResponder extends CapabilityRegistration {
  relevance: number
  confidence: number
  proposed_action: string
  timeout_ms: number
}

export interface ResponseBundle {
  message_id: string
  bundle_status: 'complete' | 'partial' | 'failed'
  selected_responders: RankedResponder[]
  suppressed_responders: number
  bundle_strategy: BundleStrategy
  audit_event_id?: string
  errors?: string[]
}

const ROUTER_POLICY = {
  weights: {
    capability_match: 0.5,
    domain_match: 0.2,
    priority: 0.1,
    latency: 0.06,
    effectiveness: 0.12,
    load_penalty: 0.08,
    cost_penalty: 0.06,
  },
  timeouts_ms: {
    fast: 250,
    normal: 800,
    slow: 1800,
  },
  degraded: {
    max_current_load: 0.92,
    min_effectiveness_score: 0.3,
    suppress_degraded_responders: true,
  },
  defaults: {
    max_responders: 5,
    bundle_strategy: 'rank_and_merge' as BundleStrategy,
  },
}

function overlapScore(a?: string[], b?: string[]): number {
  if (!a?.length || !b?.length) return 0
  const right = new Set(b)
  const hits = a.filter(item => right.has(item)).length
  return hits / Math.max(a.length, b.length)
}

function latencyBoost(latency?: CapabilityRegistration['latency_class']): number {
  if (latency === 'fast') return 1
  if (latency === 'normal') return 0.5
  return 0
}

function costPenalty(cost?: CapabilityRegistration['cost_class']): number {
  if (cost === 'high') return 1
  if (cost === 'medium') return 0.5
  return 0
}

function priorityBoost(priority?: number): number {
  if (priority == null) return 0
  return Math.min(Math.max(priority, 0), 10) / 10
}

function effectivenessBoost(effectiveness?: number): number {
  if (effectiveness == null) return 0.5
  return Math.max(0, Math.min(1, effectiveness))
}

function loadPenalty(load?: number): number {
  if (load == null) return 0
  return Math.max(0, Math.min(1, load))
}

function timeoutFor(latency?: CapabilityRegistration['latency_class']): number {
  if (latency === 'fast') return ROUTER_POLICY.timeouts_ms.fast
  if (latency === 'normal') return ROUTER_POLICY.timeouts_ms.normal
  return ROUTER_POLICY.timeouts_ms.slow
}

function shouldSuppressDegraded(responder: CapabilityRegistration): boolean {
  if (!ROUTER_POLICY.degraded.suppress_degraded_responders) return false
  if (responder.status === 'offline') return true
  if ((responder.current_load ?? 0) > ROUTER_POLICY.degraded.max_current_load) return true
  if ((responder.effectiveness_score ?? 1) < ROUTER_POLICY.degraded.min_effectiveness_score) return true
  return responder.status === 'degraded'
}

export function scoreResponder(
  envelope: M2ARequestEnvelope,
  responder: CapabilityRegistration,
): RankedResponder | null {
  if (envelope.target_scope === 'single' && envelope.target && responder.node_id !== envelope.target) {
    return null
  }

  if (envelope.target_scope === 'pillar' && envelope.target && responder.pillar !== envelope.target) {
    return null
  }

  if (envelope.target_scope === 'broadcast' && !responder.accepts_broadcast) {
    return null
  }

  if (shouldSuppressDegraded(responder)) {
    return null
  }

  const capabilityScore = overlapScore(envelope.required_capabilities, responder.capabilities)
  const domainScore = overlapScore(envelope.domains, responder.domains)
  const base =
    capabilityScore * ROUTER_POLICY.weights.capability_match +
    domainScore * ROUTER_POLICY.weights.domain_match +
    priorityBoost(responder.priority) * ROUTER_POLICY.weights.priority +
    latencyBoost(responder.latency_class) * ROUTER_POLICY.weights.latency +
    effectivenessBoost(responder.effectiveness_score) * ROUTER_POLICY.weights.effectiveness -
    loadPenalty(responder.current_load) * ROUTER_POLICY.weights.load_penalty -
    costPenalty(responder.cost_class) * ROUTER_POLICY.weights.cost_penalty

  const relevance = Math.max(0, Math.min(1, base))

  if (relevance <= 0 && envelope.routing?.suppress_irrelevant !== false) {
    return null
  }

  return {
    ...responder,
    relevance,
    confidence: Math.max(0.1, Math.min(0.99, relevance + 0.04)),
    proposed_action: envelope.intent,
    timeout_ms: timeoutFor(responder.latency_class),
  }
}

export function buildResponseBundle(
  envelope: M2ARequestEnvelope,
  responders: CapabilityRegistration[],
): ResponseBundle {
  const ranked = responders
    .map(responder => scoreResponder(envelope, responder))
    .filter((item): item is RankedResponder => item !== null)
    .sort((a, b) => b.relevance - a.relevance)

  const maxResponders = envelope.routing?.max_responders ?? ROUTER_POLICY.defaults.max_responders
  const selected = ranked.slice(0, maxResponders)
  const suppressed = Math.max(0, responders.length - selected.length)

  return {
    message_id: envelope.message_id,
    bundle_status: selected.length > 0 ? 'complete' : 'failed',
    selected_responders: selected,
    suppressed_responders: suppressed,
    bundle_strategy: envelope.routing?.bundle_strategy ?? ROUTER_POLICY.defaults.bundle_strategy,
    errors: selected.length > 0 ? [] : ['No relevant responders selected'],
  }
}
