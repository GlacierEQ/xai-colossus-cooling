import { validateApiKey } from '../auth/api-key-validation';

export async function GET(request: Request) {
  const auth = validateApiKey(request);
  if (!auth.valid) {
    return new Response(JSON.stringify({ error: auth.message }), { status: 401 });
  }

  return new Response(JSON.stringify({ data: 'thermal_snapshot' }), { status: 200 });
}

export async function POST(request: Request) {
  const auth = validateApiKey(request);
  if (!auth.valid) {
    return new Response(JSON.stringify({ error: auth.message }), { status: 401 });
  }

  return new Response(JSON.stringify({ status: 'success' }), { status: 200 });
}
