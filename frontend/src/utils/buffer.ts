/**
 * Konwertuj ArrayBufferLike (SharedArrayBuffer lub ArrayBuffer) do zwykłego ArrayBuffer
 */
export function toArrayBuffer(buffer: ArrayBufferLike): ArrayBuffer {
  if (buffer instanceof ArrayBuffer) {
    return buffer;
  }
  // SharedArrayBuffer case: copy do normalnego ArrayBuffer
  const ab = new ArrayBuffer(buffer.byteLength);
  new Uint8Array(ab).set(new Uint8Array(buffer));
  return ab;
}

/**
 * Konwertuj ArrayBufferLike do Uint8Array<ArrayBuffer> (typ-safe)
 */
export function toUint8Array(buffer: ArrayBufferLike): Uint8Array {
  const ab = toArrayBuffer(buffer);
  return new Uint8Array(ab);
}

/**
 * Konwertuj Uint8Array<ArrayBufferLike> do Uint8Array<ArrayBuffer>
 */
export function ensureUint8Array(data: Uint8Array): Uint8Array {
  if (data.buffer instanceof ArrayBuffer) {
    return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  }
  // SharedArrayBuffer case
  const ab = new ArrayBuffer(data.byteLength);
  new Uint8Array(ab).set(data);
  return new Uint8Array(ab);
}