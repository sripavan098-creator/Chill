/**
 * Minimal base64 encoder.
 *
 * Hermes has no `btoa`, and the polyfills pull in more than this needs, so the
 * small amount of encoding required for an upload lives here.
 */

const ALPHABET =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

export function encodeBase64(bytes: Uint8Array): string {
  let output = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i];
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    output += ALPHABET[a >> 2];
    output += ALPHABET[((a & 0x03) << 4) | (b >> 4)];
    output += i + 1 < bytes.length ? ALPHABET[((b & 0x0f) << 2) | (c >> 6)] : '=';
    output += i + 2 < bytes.length ? ALPHABET[c & 0x3f] : '=';
  }
  return output;
}
