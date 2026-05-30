// API key validation helper for protected thermal proxy endpoints.
// Rejects empty server keys and empty incoming keys, then performs
// a constant-time comparison to reduce timing side channels.

export function validateApiKey(request: Request) {
  const configuredKey = process.env.COLOSSUS_API_KEY || '';

  if (!configuredKey || configuredKey.trim() === '') {
    return { valid: false, message: 'API key not configured on server' };
  }

  const incomingKey = request.headers.get('x-api-key') || '';
  if (!incomingKey || incomingKey.trim() === '') {
    return { valid: false, message: 'Missing x-api-key header' };
  }

  const isValid = timingSafeCompare(configuredKey, incomingKey);
  return isValid
    ? { valid: true, message: 'Authenticated' }
    : { valid: false, message: 'Invalid API key' };
}

function timingSafeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
