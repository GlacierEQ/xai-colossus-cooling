# M2A Hardening Checklist

## Purpose

This checklist defines the final hardening pass for the M2A and MCP-to-All implementation.

## Completion meaning

The core invention and architecture are already in place.
What remains is hardening work:
- tests
- validation
- Aspen sink integration
- route/runtime verification
- final UI polish

## Final hardening items

### 1. Registry validation
- validate responder registry objects before routing
- enforce required fields
- enforce score/load ranges
- fail clearly on malformed entries

### 2. Route/runtime verification
- verify all M2A route paths resolve correctly
- verify registry file paths resolve from dashboard routes
- verify dashboard preview panels point at live route endpoints

### 3. Aspen persistence completion
- bridge route-level persistence into the real Aspen Grove sink path
- distinguish webhook mode from true Aspen connector mode
- preserve offline fallback mode for local development

### 4. Router behavior tests
- degraded responder suppression
- offline responder suppression
- timeout assignment by latency class
- pillar filtering
- bundle strategy defaults

### 5. UI polish
- bundle detail panel
- error state consistency
- optional responder explanation text
- optional latency/effectiveness badges

## Readiness definition

The implementation should be treated as complete enough to harden when:
- schemas exist
- routing exists
- registry exists
- at least one live bundle path exists
- audit trail exists

That condition has already been met.

## Bottom line

The remaining work is not foundational invention work.
It is finalization work to make the current design safer, cleaner, and more production-ready.
