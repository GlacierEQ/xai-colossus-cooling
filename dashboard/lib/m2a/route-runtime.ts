import { readFile } from 'node:fs/promises'
import path from 'node:path'

import { createRoutingAuditTrail } from './aspen-audit'
import { persistAspenAuditEvents } from './aspen-persistence'
import type { CapabilityRegistration, M2ARequestEnvelope, ResponseBundle } from './relevance-router'
import { buildResponseBundle } from './relevance-router'
import { validateResponderRegistry } from './registry-validation'

export interface M2ARouteRuntimeResult {
  envelope: M2ARequestEnvelope
  bundle: ResponseBundle
  audit: ReturnType<typeof createRoutingAuditTrail>
  persistence: Awaited<ReturnType<typeof persistAspenAuditEvents>>
  registry_validation: {
    valid: boolean
    errors: string[]
  }
}

export async function loadResponderRegistry(): Promise<CapabilityRegistration[]> {
  const registryPath = path.join(process.cwd(), '..', 'config', 'm2a', 'responder-registry.json')
  const content = await readFile(registryPath, 'utf-8')
  const responders = JSON.parse(content) as CapabilityRegistration[]

  const validation = validateResponderRegistry(responders)
  if (!validation.valid) {
    throw new Error(`Invalid responder registry: ${validation.errors.join('; ')}`)
  }

  return responders
}

export async function executeM2ARoute(
  envelope: M2ARequestEnvelope,
): Promise<M2ARouteRuntimeResult> {
  const responders = await loadResponderRegistry()
  const registryValidation = validateResponderRegistry(responders)
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

  return {
    envelope,
    bundle: {
      ...bundle,
      audit_event_id: audit.bundled.event_id,
    },
    audit,
    persistence,
    registry_validation: registryValidation,
  }
}
