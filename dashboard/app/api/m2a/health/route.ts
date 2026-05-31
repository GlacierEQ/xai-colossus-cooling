import { NextResponse } from 'next/server'
import { readFile } from 'node:fs/promises'
import path from 'node:path'

import { validateResponderRegistry } from '../../../../lib/m2a/registry-validation'

async function readRegistry() {
  const registryPath = path.join(process.cwd(), '..', 'config', 'm2a', 'responder-registry.json')
  const content = await readFile(registryPath, 'utf-8')
  return JSON.parse(content)
}

export async function GET() {
  try {
    const responders = await readRegistry()
    const validation = validateResponderRegistry(responders)

    return NextResponse.json({
      ok: validation.valid,
      registry_validation: validation,
      responder_count: responders.length,
      routes: [
        '/api/m2a/forecast',
        '/api/m2a/zone-snapshot',
        '/api/m2a/piston-status',
        '/api/m2a/pillar',
      ],
    }, {
      status: validation.valid ? 200 : 500,
    })
  } catch (error) {
    return NextResponse.json({
      ok: false,
      error: 'M2A health check failed',
      details: error instanceof Error ? error.message : String(error),
    }, { status: 500 })
  }
}
