import type { CapabilityRegistration } from './relevance-router'

export interface RegistryValidationResult {
  valid: boolean
  errors: string[]
}

function isInRange(value: unknown, min: number, max: number): boolean {
  return typeof value === 'number' && value >= min && value <= max
}

export function validateResponder(responder: Partial<CapabilityRegistration>, index = 0): RegistryValidationResult {
  const errors: string[] = []

  if (!responder.node_id || typeof responder.node_id !== 'string') {
    errors.push(`Responder[${index}] missing valid node_id`)
  }

  if (!responder.node_type || typeof responder.node_type !== 'string') {
    errors.push(`Responder[${index}] missing valid node_type`)
  }

  if (!Array.isArray(responder.capabilities) || responder.capabilities.length === 0) {
    errors.push(`Responder[${index}] missing capabilities`)
  }

  if (!Array.isArray(responder.domains) || responder.domains.length === 0) {
    errors.push(`Responder[${index}] missing domains`)
  }

  if (typeof responder.accepts_broadcast !== 'boolean') {
    errors.push(`Responder[${index}] missing accepts_broadcast boolean`)
  }

  if (responder.priority != null && !isInRange(responder.priority, 0, 10)) {
    errors.push(`Responder[${index}] priority must be between 0 and 10`)
  }

  if (responder.effectiveness_score != null && !isInRange(responder.effectiveness_score, 0, 1)) {
    errors.push(`Responder[${index}] effectiveness_score must be between 0 and 1`)
  }

  if (responder.current_load != null && !isInRange(responder.current_load, 0, 1)) {
    errors.push(`Responder[${index}] current_load must be between 0 and 1`)
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}

export function validateResponderRegistry(responders: Partial<CapabilityRegistration>[]): RegistryValidationResult {
  const errors = responders.flatMap((responder, index) => validateResponder(responder, index).errors)
  return {
    valid: errors.length === 0,
    errors,
  }
}
