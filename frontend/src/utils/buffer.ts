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