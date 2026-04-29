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
}

export interface RankedResponder extends CapabilityRegistration {
  relevance: number
  confidence: number
  proposed_action: string
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

function overlapScore(a?: string[], b?: string[]): number {
  if (!a?.length || !b?.length) return 0
  const right = new Set(b)
  const hits = a.filter(item => right.has(item)).length
  return hits / Math.max(a.length, b.length)
}

function latencyBoost(latency?: CapabilityRegistration['latency_class']): number {
  if (latency === 'fast') return 0.08
  if (latency === 'normal') return 0.03
  return 0
}

function costPenalty(cost?: CapabilityRegistration['cost_class']): number {
  if (cost === 'high') return 0.08
  if (cost === 'medium') return 0.03
  return 0
}

function priorityBoost(priority?: number): number {
  if (priority == null) return 0
  return Math.min(Math.max(priority, 0), 10) / 100
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

  const capabilityScore = overlapScore(envelope.required_capabilities, responder.capabilities)
  const domainScore = overlapScore(envelope.domains, responder.domains)
  const base = capabilityScore * 0.55 + domainScore * 0.25 + priorityBoost(responder.priority) + latencyBoost(responder.latency_class) - costPenalty(responder.cost_class)
  const relevance = Math.max(0, Math.min(1, base))

  if (relevance <= 0 && envelope.routing?.suppress_irrelevant !== false) {
    return null
  }

  return {
    ...responder,
    relevance,
    confidence: Math.max(0.1, Math.min(0.99, relevance + 0.04)),
    proposed_action: envelope.intent,
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

  const maxResponders = envelope.routing?.max_responders ?? 5
  const selected = ranked.slice(0, maxResponders)
  const suppressed = Math.max(0, responders.length - selected.length)

  return {
    message_id: envelope.message_id,
    bundle_status: selected.length > 0 ? 'complete' : 'failed',
    selected_responders: selected,
    suppressed_responders: suppressed,
    bundle_strategy: envelope.routing?.bundle_strategy ?? 'rank_and_merge',
    errors: selected.length > 0 ? [] : ['No relevant responders selected'],
  }
}
